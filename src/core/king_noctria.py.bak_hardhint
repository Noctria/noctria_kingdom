# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8
"""
👑 King Noctria (理想型 v4.0) - 五臣による統治 + PM AI (GPT) 兼用版
- 既存Kingに ModelRouter (Ollama↔GPT) を非破壊統合
- ロガー未定義の NameError を修正
- 五臣/decide系は最小スタブを同梱（実装が別にある場合は自動で差替 or 置換可）
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ----- logger 設定（先に定義して NameError 防止） -----
logger = logging.getLogger("noctria.king")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# ---- import 経路を安定化 ----
try:
    from src.core.path_config import (
        AIRFLOW_API_BASE,
        ensure_import_path,
        ensure_strategy_packages,
    )
except Exception:
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    SRC_DIR = PROJECT_ROOT / "src"
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    from src.core.path_config import (
        AIRFLOW_API_BASE,
        ensure_import_path,
        ensure_strategy_packages,
    )

ensure_import_path()
ensure_strategy_packages()

# --- ガバナンスYAML → System Prompt 合成 / 外部依存 ---
import requests  # noqa: E402
from src.core.prompt_loader import load_prompt_text, load_governance_dict  # noqa: E402

# --- ルーティング層（Ollama↔GPT） ---
try:
    from src.core.model_router import ModelRouter, RouteTask
except Exception:
    ModelRouter = None  # まだ導入前でもエラーにしない
    RouteTask = None

# -------- 依存（OrderExecution） --------
try:
    from src.execution.order_execution import OrderExecution as _OrderExecution
except Exception:
    try:
        from src.do.order_execution import OrderExecution as _OrderExecution
    except Exception:
        _OrderExecution = None


class _NoopOrderExecution:
    def __init__(self, *a, **kw):
        self._api = kw.get("api_url")

    def send(self, order: dict) -> dict:
        logger.info(f"[NOOP-ORDER] would send: {order}")
        return {"status": "noop", "order": order}


OrderExecution = _OrderExecution if _OrderExecution is not None else _NoopOrderExecution


# ----- 五臣：実装があれば自動で差し替え。無い場合はスタブ -----
class _Noop:
    name = "noop"

    def __init__(self, *a, **kw):
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


try:
    from src.veritas.veritas_machina import VeritasMachina  # 実装があれば使われる
except Exception:

    class VeritasMachina(_Noop):
        pass


try:
    from src.strategies.prometheus_oracle import PrometheusOracle
except Exception:

    class PrometheusOracle(_Noop):
        pass


try:
    from src.strategies.aurus_singularis import AurusSingularis
except Exception:

    class AurusSingularis(_Noop):
        pass


try:
    from src.strategies.levia_tempest import LeviaTempest
except Exception:

    class LeviaTempest(_Noop):
        pass


try:
    from src.hermes.strategy_generator import HermesCognitorStrategy
except Exception:

    class HermesCognitorStrategy(_Noop):
        pass


# フォールバック: NoctusSentinella が未定義ならダミーにする
if "NoctusSentinella" not in globals():

    class NoctusSentinella(_Noop):
        pass


# ------------------- 型 -------------------
@dataclass
class CouncilResult:
    decision_id: str
    timestamp: str
    final_decision: str
    raw: Dict[str, Any]


# ------------------- OpenAIクライアント（任意） -------------------
def _get_openai_client():
    """
    あなたのOpenAI初期化ロジックをここに実装していれば利用。
    未設定でも例外にせず None を返す。
    """
    try:
        # from openai import OpenAI
        # return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return None
    except Exception:
        return None


# ------------------- 共通ヘルパ -------------------
def _headers_json(api_key: Optional[str] = None) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def _extract_content_from_chat(resp_json: dict) -> str:
    """
    OpenAI互換の /v1/chat/completions からcontentを抜く。
    ベンダ差異にゆるく対応。
    """
    try:
        return resp_json["choices"][0]["message"]["content"]
    except Exception:
        if "output_text" in resp_json:
            return str(resp_json["output_text"])
        if isinstance(resp_json.get("content"), str):
            return resp_json["content"]
        # OpenAI Responses API 互換っぽい形
        if "output" in resp_json and isinstance(resp_json["output"], list):
            parts = []
            for p in resp_json["output"]:
                if isinstance(p, dict) and p.get("type") == "output_text":
                    parts.append(p.get("content", ""))
            if parts:
                return "".join(parts)
        return str(resp_json)[:1000]


# ------------------- 王 本体 -------------------
class KingNoctria:
    def __init__(self):
        logger.info("王の評議会を構成するため、五臣を招集します。")
        self.veritas = VeritasMachina()
        self.prometheus = PrometheusOracle()
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.hermes = HermesCognitorStrategy()
        self.order_executor = OrderExecution(api_url="http://host.docker.internal:5001/order")
        logger.info("五臣の招集が完了しました。")
        self._agent_cfg = _load_agent_config()

        # PM AI初期化
        self._gov: Optional[dict] = None
        self._system_prompt: Optional[str] = None
        try:
            self._gov = load_governance_dict()  # ✅ dict 返す
            self._system_prompt = load_prompt_text()  # ✅ 文字列返す
        except Exception as e:
            logger.warning(f"ガバナンスYAML読込に失敗: {e}")
            self._gov = {}
            self._system_prompt = (
                "You are Noctria 王.\n"
                "ROLE: プロジェクトのプロマネ / 最高意思決定者\n"
                "OUTPUT_FORMAT:\n"
                "- Always respond in Japanese.\n"
                "- Return a concise PLAN with numbered steps, plus RISKS and NEXT_ACTIONS.\n"
            )

        self._openai = None
        try:
            self._openai = _get_openai_client()
            logger.info("PM AI クライアントを初期化しました。")
        except Exception as e:
            logger.warning(f"PM AI クライアント初期化に失敗: {e}")

        # ルーター（必要時に遅延初期化も可）
        self._model_router: Optional[ModelRouter] = ModelRouter() if ModelRouter else None

    # ------------------- 既存王政メソッド（必要なら置換） -------------------
    def decide(self, *a, **kw) -> CouncilResult:
        """
        NOTE: 既存の実装が別にある場合はそちらを残してください。
        ここは落ちないための最小実装です。
        """
        return CouncilResult(
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            final_decision="(placeholder) use your existing decide()",
            raw={"note": "replace with project decide() if available"},
        )

    def next_actions(self, *a, **kw) -> List[str]:
        """最小実装。必要なら置換。"""
        return ["(placeholder) replace with existing next_actions()"]

    def order_trade(self, order: dict) -> dict:
        """実行は OrderExecution に委譲。"""
        return self.order_executor.send(order)

    def hold_council(self, *a, **kw) -> CouncilResult:
        """最小実装。必要なら置換。"""
        return self.decide()

    def _trigger_dag(self, dag_id: str, conf: Optional[dict] = None) -> dict:
        """Airflow DAG を叩く。実環境に合わせて拡張可。"""
        url = f"{AIRFLOW_API_BASE}/dags/{dag_id}/dagRuns"
        try:
            r = requests.post(url, json={"conf": conf or {}}, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning(f"Airflow trigger failed: {e}")
            return {"status": "failed", "reason": str(e)}

    # ------------------- ルーティング統合（新規） -------------------
    def chat_with_routing(
        self,
        user_prompt: str,
        requires_internet: bool = False,
        category: Optional[str] = None,
        analysis_level: str = "normal",
        hard_model_hint: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        既存の王政ロジックに影響を与えない“薄い”チャット入口。
        ルーターでOllama/GPTを自動選択し、呼び出し実処理は _call_* に委譲。
        """
        if ModelRouter is None or RouteTask is None:
            raise RuntimeError(
                "ModelRouter/RouteTask が見つかりません。model_router.py を導入してください。"
            )

        router = self._model_router or ModelRouter()
        self._model_router = router

        task = RouteTask(
            prompt=user_prompt,
            requires_internet=requires_internet,
            category=category,
            analysis_level=analysis_level,
            hard_model_hint=hard_model_hint,
        )
        decision = router.decide_and_prepare(task)

        messages: List[dict] = []
        if system_prompt or self._system_prompt:
            messages.append(
                {"role": "system", "content": system_prompt or self._system_prompt or ""}
            )
        messages.append({"role": "user", "content": user_prompt})

        if decision["provider"] == "ollama":
            out = self._call_ollama(
                base_url=decision["base_url"],
                model=decision["model"],
                messages=messages,
                timeout_s=decision["timeout_s"],
            )
        else:
            out = self._call_gpt(
                base_url=decision["base_url"],
                model=decision["model"],
                api_key=decision.get("api_key") or "",
                messages=messages,
                timeout_s=decision["timeout_s"],
            )

        # 説明責任ログ
        try:
            self._log_router_decision(
                side=decision["selected_side"],
                model=decision["model"],
                reason=decision["reason"],
                est_tokens=decision["estimated_tokens"],
                prompt_sample=user_prompt[:160],
            )
        except Exception:
            pass

        return {
            "selected_side": decision["selected_side"],
            "model": decision["model"],
            "reason": decision["reason"],
            "estimated_tokens": decision["estimated_tokens"],
            "output": out,
        }

    # ------------------- 実呼び出し（実API版） -------------------
    def _call_ollama(
        self, base_url: str, model: str, messages: List[dict], timeout_s: float
    ) -> Dict[str, Any]:
        """
        1) OpenAI互換 (/v1/chat/completions) を試行
        2) 失敗時は Ollama ネイティブ (/api/chat) に自動フォールバック
        """
        import requests

        def _as_chat_messages(msgs: List[dict]) -> List[dict]:
            return [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in msgs]

        # ---- 1) OpenAI互換を試す
        try:
            url_v1 = base_url.rstrip("/") + "/chat/completions"
            payload_v1 = {
                "model": model,
                "messages": _as_chat_messages(messages),
                "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
                "stream": False,
            }
            r = requests.post(
                url_v1,
                json=payload_v1,
                headers=_headers_json(None),
                timeout=float(os.getenv("OLLAMA_TIMEOUT_S", str(timeout_s))),
            )
            if r.status_code < 400:
                data = r.json()
                content = _extract_content_from_chat(data)
                return {
                    "role": "assistant",
                    "content": content,
                    "meta": {"provider": "ollama", "mode": "openai"},
                }
            logger.info(
                f"Ollama openai-compat returned {r.status_code}, falling back to native /api/chat"
            )
        except Exception as e:
            logger.info(f"Ollama openai-compat try failed ({e}); falling back to native /api/chat")

        # ---- 2) ネイティブ API (/api/chat)
        try:
            base_native = re.sub(r"/v1/?$", "", base_url.rstrip("/"))
            url_native = base_native + "/api/chat"
            payload_native = {
                "model": model,
                "messages": _as_chat_messages(messages),
                "stream": False,
                "options": {
                    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
                },
            }
            r2 = requests.post(
                url_native,
                json=payload_native,
                headers={"Content-Type": "application/json"},
                timeout=float(os.getenv("OLLAMA_TIMEOUT_S", str(timeout_s))),
            )
            r2.raise_for_status()
            data2 = r2.json()
            content = (
                data2.get("message", {}).get("content")
                or data2.get("response")
                or _extract_content_from_chat(data2)
            )
            return {
                "role": "assistant",
                "content": content,
                "meta": {"provider": "ollama", "mode": "native"},
            }
        except Exception as e2:
            logger.warning(f"Ollama native call failed: {e2}")
            return {"role": "assistant", "content": f"[Ollama error] {e2}"}

    def _call_gpt(
        self, base_url: str, model: str, api_key: str, messages: List[dict], timeout_s: float
    ) -> Dict[str, Any]:
        """
        OpenAI公式/互換の /v1/chat/completions を使用。
        （Responses APIで統一したい場合はここを書き換え）
        """
        url = base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            "stream": False,
        }
        try:
            r = requests.post(
                url,
                json=payload,
                headers=_headers_json(api_key),
                timeout=float(os.getenv("OPENAI_TIMEOUT_S", str(timeout_s))),
            )
            r.raise_for_status()
            data = r.json()
            content = _extract_content_from_chat(data)
            return {"role": "assistant", "content": content, "meta": {"provider": "gpt"}}
        except Exception as e:
            logger.warning(f"GPT call failed: {e}")
            return {"role": "assistant", "content": f"[GPT error] {e}"}

    # ------------------- 監査ログ（任意） -------------------
    def _log_router_decision(
        self, side: str, model: str, reason: str, est_tokens: int, prompt_sample: str
    ) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "side": side,
            "model": model,
            "reason": reason,
            "estimated_tokens": est_tokens,
            "prompt_sample": prompt_sample,
        }
        try:
            os.makedirs("logs", exist_ok=True)
            path = os.path.join("logs", "king_log.json")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"router log write failed: {e}")


# ------------------- エージェント設定のロード（既存挙動を踏襲） -------------------
def _load_agent_config() -> dict:
    import os

    try:
        gov = load_governance_dict()  # ✅ dictで読み込む
    except Exception:
        return {}
    agent = gov.get("agent", {}) or {}
    tools = gov.get("tools", {}) or {}
    automations = gov.get("automations", {}) or {}
    routing = gov.get("routing", {}) or {}
    memory_policy = gov.get("memory_policy", {}) or {}
    if os.getenv("NOCTRIA_AGENT_ENABLE"):
        agent["enabled"] = os.getenv("NOCTRIA_AGENT_ENABLE") == "1"
    if os.getenv("NOCTRIA_AGENT_MAX_STEPS"):
        agent["max_steps"] = int(os.getenv("NOCTRIA_AGENT_MAX_STEPS"))
    return {
        "agent": agent,
        "tools": tools,
        "automations": automations,
        "routing": routing,
        "memory_policy": memory_policy,
    }


# ------------------- スタンドアロン実行（スモーク） -------------------
if __name__ == "__main__":
    try:
        k = KingNoctria()
        demo = k.chat_with_routing(
            "ルーティングの動作確認用に、短い返答をください。",
            requires_internet=False,
            category="dev",
            analysis_level="light",
        )
        print(json.dumps(demo, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error(f"chat_with_routing failed: {e}")
