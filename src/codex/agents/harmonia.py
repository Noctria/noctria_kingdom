# src/codex/agents/harmonia.py
from __future__ import annotations

import datetime as dt
import json
import logging
import math
import os
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .inventor import InventorOutput, PatchSuggestion

# =============================================================================
# Logger（Airflow タスクロガーに寄せつつ、ローカル単体実行でも動作）
# =============================================================================
LOGGER = logging.getLogger("airflow.task")
if not LOGGER.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

HARMONIA_SYSTEM_PROMPT = """\
あなたは Noctria 王国のレビュワーAI『Harmonia Ordinis』です。
役割: 提案パッチの妥当性・後方互換・王国方針整合を審査し、必要なら修正指示を返す。
審査観点:
- 変更が最小か？副作用は？contractsの破壊はないか？
- テスト分離方針（軽量/重）と整合しているか？
- observability/logging が妥当か？
出力形式:
- "verdict": APPROVE / REVISE
- "comments": 箇条書き
"""


# =============================================================================
# モード・重み設定
# =============================================================================
def _env_mode() -> str:
    mode = os.getenv("NOCTRIA_HARMONIA_MODE", "offline").strip().lower()
    return mode if mode in {"offline", "api", "auto"} else "offline"


_DEFAULT_WEIGHTS = {
    "quality": 1.00,
    "risk_adj": 0.90,
    "risk": 0.60,
    "size": 0.25,
}


def _load_weights() -> Dict[str, float]:
    raw = os.getenv("HARMONIA_WEIGHTS", "").strip()
    if not raw:
        return dict(_DEFAULT_WEIGHTS)
    try:
        data = json.loads(raw)
        w = dict(_DEFAULT_WEIGHTS)
        for k, v in (data or {}).items():
            if isinstance(v, (int, float)) and k in w:
                w[k] = float(v)
        return w
    except Exception:
        LOGGER.warning("HARMONIA_WEIGHTS のJSON解釈に失敗。デフォルトを使用します。")
        return dict(_DEFAULT_WEIGHTS)


# =============================================================================
# 型
# =============================================================================
@dataclass
class ReviewResult:
    verdict: str  # "APPROVE" | "REVISE"
    comments: List[str]
    generated_at: str = dt.datetime.now(tz=dt.timezone(dt.timedelta(hours=9))).isoformat(
        timespec="seconds"
    )
    trace_id: Optional[str] = None


# =============================================================================
# 本体
# =============================================================================
class HarmoniaOrdinis:
    """
    Harmonia レビュー実装（Lv1ベース → 強化）
    """

    # ===== 低レベルチェック =====
    def _check_minimal_change(self, ps: PatchSuggestion) -> Optional[str]:
        if not ps.pseudo_diff or ps.pseudo_diff.strip() in {
            "(N/A)",
            "(N/A: まず再現最小化とデバッグログ挿入で原因特定)",
        }:
            return f"`{ps.file}` の差分が不明瞭。最小差分の擬似diffを提示してください。"
        if "from .* import *" in ps.pseudo_diff:
            return "ワイルドカード import は副作用が読めないため不可。限定 import で。"
        return None

    def _check_backward_compat(self, ps: PatchSuggestion) -> Optional[str]:
        risky = any(key in ps.pseudo_diff for key in ["delete", "remove", "rename(", "deprecated"])
        if risky:
            return "後方互換を損ねる可能性がある変更が含まれます。契約(API/スキーマ)の互換を維持してください。"
        return None

    def _check_observability(self, ps: PatchSuggestion) -> Optional[str]:
        if "quality_gate" in ps.file or "risk" in ps.file or "adapter" in ps.file:
            return "重要経路の修正です。`observability.py` 相当のログ/メトリクス追跡を検討してください。"
        return None

    def _check_project_specific(self, ps: PatchSuggestion) -> List[str]:
        notes: List[str] = []
        if "strategy_adapter.py" in ps.file and (
            "dict()" in ps.pseudo_diff or "model_dump" in ps.pseudo_diff
        ):
            notes.append(
                "pydantic v1 (`.dict()`) / v2 (`.model_dump()`) 両対応メモを備考に追記してください。"
            )
        return notes

    # ===== 構造化レビュー =====
    def review_structured(self, inventor_out: InventorOutput) -> ReviewResult:
        comments: List[str] = []
        verdict = "APPROVE"

        if not getattr(inventor_out, "patch_suggestions", None):
            comments.append("パッチ案が空。最低1件は具体差分を提示してください。")
            return ReviewResult(verdict="REVISE", comments=comments, trace_id=inventor_out.trace_id)

        for ps in inventor_out.patch_suggestions:
            if ps.file.startswith("(検出できず)"):
                comments.append(
                    "修正対象の特定が曖昧。具体ファイル・関数・差分を明記して再提案を。"
                )
                verdict = "REVISE"

            msg = self._check_minimal_change(ps)
            if msg:
                comments.append(msg)
                verdict = "REVISE"

            msg = self._check_backward_compat(ps)
            if msg:
                comments.append(msg)
                verdict = "REVISE"

            msg = self._check_observability(ps)
            if msg:
                comments.append(msg)

            comments.extend(self._check_project_specific(ps))

        if not getattr(inventor_out, "followup_tests", None):
            comments.append("追試案が未提示。`pytest -q -k <nodeid>` を明記してください。")
            verdict = "REVISE"

        LOGGER.info(
            "[Harmonia] review_structured verdict=%s comments=%d trace_id=%s",
            verdict,
            len(comments),
            inventor_out.trace_id,
        )
        return ReviewResult(verdict=verdict, comments=comments, trace_id=inventor_out.trace_id)

    # ===== Markdown レビュー（mini_loop 用） =====
    def review_markdown(
        self,
        failures: List[Dict[str, Any]],
        inventor_suggestions: str,
        principles: List[str],
    ) -> str:
        def _check_completeness() -> str:
            notes = []
            for f in failures:
                nodeid = f.get("nodeid", "")
                if nodeid and (nodeid not in inventor_suggestions):
                    notes.append(f"- `{nodeid}` への具体提案なし")
            return "✅ 全失敗ケースに対応。" if not notes else "⚠️ 網羅性不足:\n" + "\n".join(notes)

        def _check_side_effects() -> str:
            risky = any(
                k in inventor_suggestions.lower()
                for k in ["# pragma: no cover", "pass  # todo", "except:"]
            )
            return "⚠️ 隠蔽的修正の可能性あり。" if risky else "✅ 大きな副作用なし。"

        def _check_guidelines() -> str:
            return "📐 方針:\n" + "\n".join(f"- {p}" for p in principles)

        def _check_repro() -> str:
            ok = (
                "pytest -q -k" in inventor_suggestions
                or "python -m codex.mini_loop" in inventor_suggestions
            )
            return "✅ 再現手順あり。" if ok else "⚠️ 再現手順不足。"

        header = "# 🧭 Harmonia Ordinis — レビュー（Lv1）\n\n"
        if not failures:
            return header + "✅ 失敗なし。レビュー不要。\n"

        body = "\n\n".join(
            [
                _check_completeness(),
                _check_side_effects(),
                _check_guidelines(),
                _check_repro(),
            ]
        )
        tail = textwrap.dedent(
            """
        ---
        #### 次のアクション
        1. 影響範囲の小さい修正を優先
        2. 失敗再現の最小テストを追加
        3. `pytest -q --maxfail=20 --durations=10` で全体再実行
        """
        )
        return header + body + "\n" + tail

    # ===== 構造化結果 → Markdown =====
    def to_markdown(self, result: ReviewResult) -> str:
        lines = ["# 🧭 Harmonia Ordinis — レビュー（Lv1）", ""]
        lines.append(f"- Verdict: **{result.verdict}**")
        lines.append(f"- Generated: `{result.generated_at}`")
        if result.trace_id:
            lines.append(f"- Trace ID: `{result.trace_id}`")
        if result.comments:
            lines.append("\n## Comments")
            for c in result.comments:
                lines.append(f"- {c}")
        return "\n".join(lines)


# =============================================================================
# 既存互換 API
# =============================================================================
def _api_review(inventor_out: InventorOutput) -> Optional[ReviewResult]:
    try:
        import openai  # type: ignore
    except Exception:
        LOGGER.warning("openai 未導入のため APIレビューはスキップします。")
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_NOCTRIA")
    if not api_key:
        LOGGER.warning("OPENAI_API_KEY が未設定のため APIレビューはスキップします。")
        return None

    try:
        payload = {
            "patch_count": len(getattr(inventor_out, "patch_suggestions", []) or []),
            "followup_tests": bool(getattr(inventor_out, "followup_tests", None)),
            "files": [
                getattr(ps, "file", "")
                for ps in (getattr(inventor_out, "patch_suggestions", []) or [])
            ][:10],
        }
        resp = openai.chat.completions.create(  # type: ignore
            model=model,
            messages=[
                {"role": "system", "content": HARMONIA_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        LOGGER.exception("APIレビューに失敗: %s", e)
        return None

    verdict = "APPROVE" if "approve" in text.lower() else "REVISE"
    comments = [c for c in text.split("\n") if c.strip()][:20]
    return ReviewResult(verdict=verdict, comments=comments, trace_id=inventor_out.trace_id)


def review(inventor_out: InventorOutput) -> ReviewResult:
    harmonia = HarmoniaOrdinis()
    base = harmonia.review_structured(inventor_out)

    mode = _env_mode()
    if mode == "offline":
        return base

    api_res = _api_review(inventor_out)
    if api_res is None:
        return base

    verdict = "REVISE" if (base.verdict != "APPROVE" or api_res.verdict != "APPROVE") else "APPROVE"
    comments = list(base.comments)
    for c in api_res.comments:
        if c not in comments:
            comments.append(c)
        if len(comments) >= 40:
            break
    return ReviewResult(verdict=verdict, comments=comments, trace_id=inventor_out.trace_id)


# =============================================================================
# Harmonia リランク
# =============================================================================
def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if hasattr(obj, key):
        try:
            return getattr(obj, key)
        except Exception:
            pass
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _intent_for_bonus(obj: Any) -> str:
    raw = (_safe_get(obj, "intent", "") or "").upper()
    if raw in {"LONG", "SHORT", "FLAT"}:
        return raw
    if raw == "BUY":
        return "LONG"
    if raw == "SELL":
        return "SHORT"
    return "FLAT"


def _get_num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str) and x.strip() != "":
            return float(x)
        return default
    except Exception:
        return default


def _peek(proposal: Any, *names: str, default: float = 0.0) -> float:
    for n in names:
        if isinstance(proposal, dict) and n in proposal:
            return _get_num(proposal.get(n), default)
        if hasattr(proposal, n):
            return _get_num(getattr(proposal, n), default)
    return default


def _score_weighted(p: Any, w: Dict[str, float]) -> float:
    q = _peek(p, "quality", "score_quality", default=0.0)
    ra = _peek(p, "risk_adjusted", "risk_adj", default=0.0)
    r = _peek(p, "risk_score", "risk", default=0.0)
    sz = _peek(p, "qty_raw", "size", default=0.0)
    size_penalty = math.log1p(max(0.0, sz))
    return (w["quality"] * q) + (w["risk_adj"] * ra) - (w["risk"] * r) - (w["size"] * size_penalty)


def rerank_candidates(
    candidates: List[Any] | Iterable[Any],
    context: Optional[Dict[str, Any]] = None,
    quality: Optional[Dict[str, Any]] = None,
) -> List[Any]:
    mode = os.getenv("HARMONIA_RERANK", "simple").strip().lower()
    ctx = context or {}
    q = quality or {}

    if mode != "weighted":
        try:
            missing = float(_safe_get(q, "missing_ratio", 0.0) or 0.0)
        except Exception:
            missing = 0.0
        try:
            lag = float(_safe_get(ctx, "data_lag_min", _safe_get(q, "data_lag_min", 0.0)) or 0.0)
        except Exception:
            lag = 0.0

        scored: List[Tuple[float, Any]] = []
        base_list = list(candidates or [])
        for c in base_list:
            base = _safe_get(c, "risk_score", 0.5)
            try:
                base = float(base if base is not None else 0.5)
            except Exception:
                base = 0.5

            intent_std = _intent_for_bonus(c)
            side_bonus = 0.01 if intent_std == "LONG" else 0.0
            penalty = max(0.0, 1.0 - missing * 2.0) * (1.0 if lag <= 5.0 else 0.8)
            adj = base * penalty + side_bonus

            try:
                setattr(c, "risk_score", base)
                setattr(c, "risk_adjusted", adj)
            except Exception:
                if isinstance(c, dict):
                    c["risk_score"] = base
                    c["risk_adjusted"] = adj

            scored.append((adj, c))

        scored.sort(key=lambda t: t[0], reverse=True)
        ranked = [c for _, c in scored]
        try:
            LOGGER.info(
                "[Harmonia] reranked(simple) %d -> %d top_intent=%s trace=%s",
                len(base_list),
                len(ranked),
                _intent_for_bonus(ranked[0]) if ranked else None,
                ctx.get("trace_id"),
            )
        except Exception:
            pass
        return ranked

    w = _load_weights()
    scored_w: List[Tuple[float, Any]] = []
    base_list = list(candidates or [])
    for p in base_list:
        s = _score_weighted(p, w)
        try:
            if isinstance(p, dict):
                p["__harmonia_score"] = s
            else:
                setattr(p, "__harmonia_score", s)
        except Exception:
            pass
        scored_w.append((s, p))

    ranked_w = [p for _, p in sorted(scored_w, key=lambda t: t[0], reverse=True)]
    try:
        LOGGER.info(
            "[Harmonia] reranked(weighted) %d -> %d top_scores=%s",
            len(base_list),
            len(ranked_w),
            [getattr(p, "__harmonia_score", None) for p in ranked_w[:3]],
        )
    except Exception:
        pass
    return ranked_w
