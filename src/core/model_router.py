# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8
"""
src/core/model_router.py

Ollama ↔ GPT の自動ルーティング層。
- 軽量/短文/低リスク → ローカル（Ollama）
- 重量/長文/高リスク/要Web要件 → クラウド（GPT）
- ポリシーは env と YAML(router_policy.yaml) で上書き可能
- ヘルスチェック、フェイルオーバ、理由文字列（explainability）を返す

依存: pyyaml (任意/あれば読み込む), python 3.10+
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import os
import time
import re
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # YAMLが無くても動く（envのみで運用）


# -------------------------
# データ構造
# -------------------------
@dataclass
class ModelEndpoint:
    provider: str  # "ollama" | "gpt"
    base_url: str  # http(s)://...
    model: str  # "llama3.1:8b-instruct-q4_K_M" など
    api_key_env: Optional[str]  # GPT系のみ: OPENAI_API_KEY 等
    timeout_s: float = 60.0


@dataclass
class RouterPolicy:
    max_local_tokens: int = 1200
    prefer_cloud_for: Tuple[str, ...] = ("governance", "ml_training", "web_search", "long_doc")
    hard_cloud_if_internet: bool = True
    latency_budget_ms: int = 2000
    cost_sensitivity: float = 0.5  # 0.0(気にしない)〜1.0(強く気にする)
    safety_bias: float = 0.4  # 0.0(攻め)〜1.0(安全側=クラウド寄り)


@dataclass
class RouteTask:
    prompt: str
    requires_internet: bool = False
    category: Optional[str] = None  # "governance" "dev" "research" など
    analysis_level: str = "normal"  # "light" | "normal" | "deep"
    hard_model_hint: Optional[str] = None  # 直接モデル指定があれば優先
    max_tokens: Optional[int] = None


@dataclass
class RouteDecision:
    endpoint: ModelEndpoint
    reason: str
    estimated_tokens: int
    selected_side: str  # "local" | "cloud"


# -------------------------
# ユーティリティ
# -------------------------
def _token_estimate(text: str) -> int:
    # ざっくり: 1 token ≈ 4 chars
    return max(1, int(len(text) / 4))


def _load_yaml_policy(path: Path) -> Dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _bool_env(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


# -------------------------
# ルーター本体
# -------------------------
class ModelRouter:
    def __init__(
        self,
        policy_file: Optional[str] = "docs/governance/router_policy.yaml",
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        self.root = root

        # エンドポイント（環境変数で上書き可能）
        self.ollama = ModelEndpoint(
            provider="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:8001/v1"),
            model=os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M"),
            api_key_env=None,
            timeout_s=float(os.getenv("OLLAMA_TIMEOUT_S", "60")),
        )
        self.gpt = ModelEndpoint(
            provider="gpt",
            base_url=os.getenv(
                "OPENAI_API_BASE", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            ),
            model=os.getenv("DEFAULT_GPT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
            api_key_env=os.getenv("OPENAI_API_KEY_VAR", "OPENAI_API_KEY"),
            timeout_s=float(os.getenv("OPENAI_TIMEOUT_S", "90")),
        )

        # ポリシー: env → YAML の順にマージ
        yaml_policy = _load_yaml_policy(root / policy_file) if policy_file else {}
        self.policy = RouterPolicy(
            max_local_tokens=int(
                os.getenv("ROUTER_MAX_LOCAL_TOKENS", str(yaml_policy.get("max_local_tokens", 1200)))
            ),
            prefer_cloud_for=tuple(
                os.getenv(
                    "ROUTER_PREFER_CLOUD_FOR",
                    ",".join(
                        yaml_policy.get(
                            "prefer_cloud_for",
                            ["governance", "ml_training", "web_search", "long_doc"],
                        )
                    ),
                ).split(",")
            )
            if (os.getenv("ROUTER_PREFER_CLOUD_FOR") or yaml_policy.get("prefer_cloud_for"))
            else (),
            hard_cloud_if_internet=_bool_env(
                "ROUTER_HARD_CLOUD_IF_INTERNET",
                bool(yaml_policy.get("hard_cloud_if_internet", True)),
            ),
            latency_budget_ms=int(
                os.getenv(
                    "ROUTER_LATENCY_BUDGET_MS", str(yaml_policy.get("latency_budget_ms", 2000))
                )
            ),
            cost_sensitivity=float(
                os.getenv("ROUTER_COST_SENSITIVITY", str(yaml_policy.get("cost_sensitivity", 0.5)))
            ),
            safety_bias=float(
                os.getenv("ROUTER_SAFETY_BIAS", str(yaml_policy.get("safety_bias", 0.4)))
            ),
        )

        # 簡易ヘルスキャッシュ
        self._health_cache: Dict[str, Tuple[float, bool, str]] = {}  # key -> (ts, ok, msg)
        self._health_ttl = 15.0

    # ---- ヘルスチェック（簡易。実際のHTTPは不要な軽量版＝即導入可能） ----
    def _health(self, side: str) -> Tuple[bool, str]:
        """
        side: "local" | "cloud"
        現段階では「環境変数の存在/URLの体裁」で静的判定。
        将来HTTP /models/ping を入れたらここに実装。
        """
        now = time.time()
        if side in self._health_cache:
            ts, ok, msg = self._health_cache[side]
            if now - ts < self._health_ttl:
                return ok, msg

        if side == "local":
            ok = bool(self.ollama.base_url.startswith("http"))
            msg = f"OLLAMA_BASE_URL={self.ollama.base_url}"
        else:
            api_key_val = os.getenv(self.gpt.api_key_env or "", "")
            ok = bool(self.gpt.base_url.startswith("http")) and bool(
                api_key_val and api_key_val != "REPLACE_ME"
            )
            msg = f"OPENAI_BASE={self.gpt.base_url}, KEY_VAR={self.gpt.api_key_env}, set={bool(api_key_val)}"

        self._health_cache[side] = (now, ok, msg)
        return ok, msg

    # ---- 複雑度スコア（0〜1） ----
    def _complexity_score(self, task: RouteTask, est_tokens: int) -> float:
        score = 0.0
        # トークン長で基礎点
        if est_tokens > self.policy.max_local_tokens:
            score += 0.5
        elif est_tokens > self.policy.max_local_tokens * 0.7:
            score += 0.25

        # 解析深度
        if task.analysis_level == "deep":
            score += 0.3
        elif task.analysis_level == "normal":
            score += 0.1

        # コード/表/箇条書きの多さで微加点
        if "```" in task.prompt:
            score += 0.15
        if re.search(r"\n- |\n\d+\.", task.prompt):
            score += 0.05

        # カテゴリ優先
        if task.category and task.category in self.policy.prefer_cloud_for:
            score += 0.3

        # インターネット必須
        if task.requires_internet and self.policy.hard_cloud_if_internet:
            score = 1.0

        # 安全バイアス
        score = min(1.0, score * (1.0 + self.policy.safety_bias * 0.5))
        return score

    # ---- ルーティング決定 ----
    def route(self, task: RouteTask) -> RouteDecision:
        est = _token_estimate(task.prompt if task.prompt else "")
        local_ok, local_msg = self._health("local")
        cloud_ok, cloud_msg = self._health("cloud")

        # ハードヒントは最優先
        if task.hard_model_hint:
            hint = task.hard_model_hint.lower()
            if "llama" in hint or "q4" in hint or "ollama" in hint:
                if not local_ok and cloud_ok:
                    # フェイルオーバ
                    return RouteDecision(
                        endpoint=self.gpt,
                        reason=f"hard_model_hint={task.hard_model_hint} requested local, but local unhealthy → fallback to cloud ({cloud_msg})",
                        estimated_tokens=est,
                        selected_side="cloud",
                    )
                return RouteDecision(
                    self.ollama, f"hard_model_hint={task.hard_model_hint}", est, "local"
                )
            else:
                if not cloud_ok and local_ok:
                    return RouteDecision(
                        endpoint=self.ollama,
                        reason=f"hard_model_hint={task.hard_model_hint} requested cloud, but cloud unhealthy → fallback to local ({local_msg})",
                        estimated_tokens=est,
                        selected_side="local",
                    )
                return RouteDecision(
                    self.gpt, f"hard_model_hint={task.hard_model_hint}", est, "cloud"
                )

        # 通常判定
        complexity = self._complexity_score(task, est)

        # しきい値：0.5以上はクラウド寄せ
        prefer_cloud = complexity >= 0.5

        # インターネット必須は原則クラウド
        if task.requires_internet and self.policy.hard_cloud_if_internet:
            prefer_cloud = True

        # サイド選択（ヘルスとフェイルオーバ考慮）
        if prefer_cloud:
            if cloud_ok:
                return RouteDecision(
                    self.gpt, f"complexity={complexity:.2f} → cloud ({cloud_msg})", est, "cloud"
                )
            elif local_ok:
                return RouteDecision(
                    self.ollama,
                    f"complexity={complexity:.2f} but cloud unhealthy → fallback local ({local_msg})",
                    est,
                    "local",
                )
            else:
                # どちらもNG（設定漏れ等）
                return RouteDecision(
                    self.gpt,
                    f"both unhealthy (local:{local_msg} / cloud:{cloud_msg}) → pick cloud by default",
                    est,
                    "cloud",
                )
        else:
            if local_ok:
                return RouteDecision(
                    self.ollama, f"complexity={complexity:.2f} → local ({local_msg})", est, "local"
                )
            elif cloud_ok:
                return RouteDecision(
                    self.gpt,
                    f"complexity={complexity:.2f} but local unhealthy → fallback cloud ({cloud_msg})",
                    est,
                    "cloud",
                )
            else:
                return RouteDecision(
                    self.ollama,
                    f"both unhealthy (local:{local_msg} / cloud:{cloud_msg}) → pick local by default",
                    est,
                    "local",
                )

    # ---- 実行ヘルパ（実際のAPI呼び出しは既存コードに委譲する前提の薄いラッパ） ----
    def decide_and_prepare(self, task: RouteTask) -> Dict[str, Any]:
        """
        返り値は呼び出し側（king_noctria.py 等）でそのまま使える情報。
        実際のAPIコールは各側の既存実装に委譲する。
        """
        dec = self.route(task)
        payload = {
            "provider": dec.endpoint.provider,
            "base_url": dec.endpoint.base_url,
            "model": dec.endpoint.model,
            "timeout_s": dec.endpoint.timeout_s,
            "api_key": os.getenv(dec.endpoint.api_key_env, "")
            if dec.endpoint.api_key_env
            else None,
            "reason": dec.reason,
            "estimated_tokens": dec.estimated_tokens,
            "selected_side": dec.selected_side,
        }
        return payload
