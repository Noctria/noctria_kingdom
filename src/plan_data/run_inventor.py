# src/plan_data/run_inventor.py
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# =============================================================================
# Logger（Airflow寄せ。ローカルでも動作）
# =============================================================================
LOGGER = logging.getLogger("airflow.task")
if not LOGGER.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

# =============================================================================
# 依存解決（複数パスに耐える）
#  - Airflow 環境や venv 実行で import ルートが異なるケースに対応
# =============================================================================
inventor_mod = None
harmonia_mod = None

# inventor
if inventor_mod is None:
    try:
        # 推奨（srcパス経由）
        from src.plan_data import inventor as inventor_mod  # type: ignore
    except Exception:
        pass
if inventor_mod is None:
    try:
        # 既存互換
        from plan_data import inventor as inventor_mod  # type: ignore
    except Exception:
        pass
if inventor_mod is None:
    try:
        # 相対（同一パッケージ）
        from . import inventor as inventor_mod  # type: ignore
    except Exception as e:
        raise ImportError("inventor module could not be imported") from e

# harmonia
if harmonia_mod is None:
    try:
        # 現在の構成は src/codex/agents/harmonia.py
        from src.codex.agents import harmonia as harmonia_mod  # type: ignore
    except Exception:
        pass
if harmonia_mod is None:
    try:
        from codex.agents import harmonia as harmonia_mod  # type: ignore
    except Exception:
        pass
if harmonia_mod is None:
    try:
        # 相対フォールバック（プロジェクトによりけり）
        from ...codex.agents import harmonia as harmonia_mod  # type: ignore
    except Exception as e:
        raise ImportError("harmonia module could not be imported") from e


# =============================================================================
# ユーティリティ
# =============================================================================
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_trace_id() -> str:
    return f"invharm-{uuid.uuid4().hex[:12]}"


# =============================================================================
# フォールバックロジック（size==0 の時）
# =============================================================================
def _fallback_size(decision: Dict[str, Any], ranked: List[Any]) -> bool:
    """
    size==0 の場合のフォールバック。
    - qty_raw / risk_score を使って最小ロットを決める簡易実装（重依存なし）
    戻り値: 適用したら True
    """
    try:
        if (decision.get("size") or 0) > 0:
            return False
        top = ranked[0] if ranked else None
        qty_raw = getattr(top, "qty_raw", None) if top else None
        risk_score = getattr(top, "risk_score", None) if top else None

        base = 0.01  # 最小ロットのベース
        bump = 0.0
        if isinstance(qty_raw, (int, float)):
            bump += float(qty_raw) * 0.001
        if isinstance(risk_score, (int, float)):
            bump += max(0.0, min(float(risk_score), 1.0)) * 0.02

        size = round(base + bump, 3)
        if size <= 0:
            size = base
        decision["size"] = size
        # reason 追記（None 安全）
        prev = decision.get("reason")
        decision["reason"] = (f"{prev} | " if prev else "") + "fallback:size"
        return True
    except Exception as e:
        LOGGER.warning("fallback_size failed: %s", e)
        return False


def _decision_from_ranked(ranked: List[Any]) -> Dict[str, Any]:
    """
    最上位提案から超軽量の意思決定を作る。
    """
    try:
        if not ranked:
            return {"side": "FLAT", "size": 0.0, "reason": "no_proposals"}
        top = ranked[0]
        side = getattr(top, "intent", "BUY")
        if side not in ("BUY", "SELL"):
            side = "BUY"
        # 初期は size=0（フォールバックで上書き想定）
        return {"side": side, "size": 0.0, "reason": "ranked_top"}
    except Exception as e:
        LOGGER.warning("decision_from_ranked failed: %s", e)
        return {"side": "FLAT", "size": 0.0, "reason": "decision_error"}


# =============================================================================
# メイン：Inventor -> Harmonia -> Decision
# =============================================================================
def run_inventor_and_decide(
    bundle: Optional[Dict[str, Any]] = None,
    *,
    artifact_path: Optional[str] = None,
    **_,
) -> Dict[str, Any]:
    """
    軽量E2E：Inventor -> Harmonia -> Decision

    Parameters
    ----------
    bundle : dict | None
        {"context": {"symbol": "...", "timeframe": "...", "trace_id": "..."},
         "features": {...} など任意}
    artifact_path : str | None
        結果をJSON保存するパス（任意）。例: "codex_reports/inventor_last.json"
        None の場合は保存しない。
    **_ :
        余剰kwargsは受け流し（DAGパラメータ互換）
    """
    # ---- Context 正規化 ----
    bundle = bundle or {}
    context = dict(bundle.get("context") or {})
    symbol = context.get("symbol") or os.getenv("NOCTRIA_DEFAULT_SYMBOL", "USDJPY")
    timeframe = context.get("timeframe") or os.getenv("NOCTRIA_DEFAULT_TIMEFRAME", "M15")
    trace_id = context.get("trace_id") or _make_trace_id()
    context.update({"symbol": symbol, "timeframe": timeframe, "trace_id": trace_id})

    # ---- 1) Inventor 提案生成 ----
    try:
        proposals = inventor_mod.generate_proposals(context) or []
    except Exception as e:
        LOGGER.exception("inventor.generate_proposals failed: %s", e)
        proposals = []

    # ---- 2) Harmonia リランク ----
    try:
        ranked = harmonia_mod.rerank_candidates(proposals, context=context) or []
    except Exception as e:
        LOGGER.exception("harmonia.rerank_candidates failed: %s", e)
        ranked = []

    # ---- 3) Decision（size はフォールバックで最終確定）----
    decision = _decision_from_ranked(ranked)
    applied = _fallback_size(decision, ranked)

    # ---- 観測ログ（Airflow ロガー）----
    try:
        LOGGER.info(
            "[Harmonia] reranked %s -> %s top=%s symbol=%s tf=%s trace=%s",
            len(proposals or []),
            len(ranked or []),
            (getattr(ranked[0], "intent", None) if ranked else None),
            symbol,
            timeframe,
            trace_id,
        )
        if applied:
            LOGGER.info(
                "[Decision] fallback_size_applied size=%s trace=%s",
                decision["size"],
                trace_id,
            )
    except Exception:
        # ログは落とさない
        pass

    # ---- 返却（XCom軽量化のため dict のみ）----
    result: Dict[str, Any] = {
        "trace_id": trace_id,
        "context": {"symbol": symbol, "timeframe": timeframe},
        "decision": decision,
        "meta": {
            "created_at": _now_iso(),
            "ranked_top_quality": (getattr(ranked[0], "quality", None) if ranked else None),
            "proposals_count": len(proposals),
        },
    }

    # ---- アーティファクト（任意保存）----
    if artifact_path:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(artifact_path)), exist_ok=True)
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            LOGGER.info("Artifact saved: %s trace=%s", artifact_path, trace_id)
        except Exception as e:
            LOGGER.warning("artifact save failed: %s (%s)", artifact_path, e)

    # ---- デバッグ用（Airflowログで見やすい1行JSON）----
    try:
        LOGGER.info("Returned value was: %s", json.dumps(result, ensure_ascii=False))
    except Exception:
        # 文字化け等で失敗しても本体返却は継続
        LOGGER.info("Returned value was: %s", str(result))

    return result
