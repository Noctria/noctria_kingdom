# src/plan_data/run_inventor.py
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Sequence

# --- ローカル依存 ---
from plan_data.inventor import generate_proposals  # 候補生成（StrategyProposal* の配列）
from decision.decision_engine import DecisionEngine

# FeatureBundle / FeatureContext は pydantic v1/v2 を意識して attr アクセスで扱う
try:
    from plan_data.quality_gate import FeatureBundle, FeatureContext  # type: ignore
except Exception:  # 後方互換のためのフェイルセーフ
    FeatureBundle = Any  # type: ignore
    FeatureContext = Any  # type: ignore

log = logging.getLogger(__name__)


# =========================
# ユーティリティ
# =========================
def _uuid() -> str:
    return str(uuid.uuid4())


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """
    pydantic(v1/v2)/dataclass/dict をまたいで安全に値を取得。
    """
    # 属性
    if hasattr(obj, key):
        try:
            return getattr(obj, key)
        except Exception:
            pass
    # dict
    if isinstance(obj, dict):
        try:
            return obj.get(key, default)
        except Exception:
            return default
    return default


def _to_dict(obj: Any) -> Dict[str, Any]:
    """
    pydantic v2(model_dump) / v1(dict) / dataclass / その他 に対応して dict 化。
    """
    if obj is None:
        return {}
    # pydantic v2
    md = getattr(obj, "model_dump", None)
    if callable(md):
        try:
            return md()
        except Exception:
            pass
    # pydantic v1
    d = getattr(obj, "dict", None)
    if callable(d):
        try:
            return d()
        except Exception:
            pass
    # dataclass
    try:
        from dataclasses import asdict, is_dataclass

        if is_dataclass(obj):
            return asdict(obj)
    except Exception:
        pass
    # フォールバック
    try:
        return dict(obj)  # type: ignore[arg-type]
    except Exception:
        return {}


def _summarize_proposals(proposals: Sequence[Any], k: int = 10) -> List[Dict[str, Any]]:
    """
    StrategyProposal*(pydantic) / dict 混在でも落ちないサマリ。
    """
    out: List[Dict[str, Any]] = []
    for p in list(proposals or [])[:k]:
        out.append(
            {
                "strategy": _get(p, "strategy", None)
                or _get(p, "name", None),  # 古いフィールド名をフォールバック
                "intent": _get(p, "intent", None),
                "qty": _get(p, "qty_raw", _get(p, "qty", None)),
                "score": _get(p, "risk_adjusted", _get(p, "risk_score", None)),
                "id": _get(p, "id", None),
            }
        )
    return out


def _fallback_size(decision: Dict[str, Any], proposals: Sequence[Any]) -> bool:
    """
    decision.size が 0/未設定 の場合に、候補の qty×risk から**安全側で**最小サイズを付与。
    戻り値: フォールバック適用の有無
    """
    try:
        size = float(_get(decision, "size", 0) or 0.0)
    except Exception:
        size = 0.0
    if size > 0:
        return False

    best = proposals[0] if proposals else None
    try:
        qty = float(_get(best, "qty_raw", _get(best, "qty", 0.0)) or 0.0) if best is not None else 0.0
    except Exception:
        qty = 0.0
    try:
        risk = float(_get(best, "risk_adjusted", _get(best, "risk_score", 0.5)) or 0.5) if best is not None else 0.5
    except Exception:
        risk = 0.5

    patched = max(1e-3, qty * max(0.1, risk))  # 下限を設け、ゼロ回避
    decision["size"] = patched
    # reason 追記（存在すれば連結）
    try:
        prev = decision.get("reason", "") or ""
        decision["reason"] = (prev + " [fallback_size_applied(qty*risk)]").strip()
    except Exception:
        decision["reason"] = "[fallback_size_applied(qty*risk)]"
    return True


def _ensure_bundle(bundle_like: Any) -> FeatureBundle:
    """
    dict 等で渡された場合でも FeatureBundle を構築。
    既に FeatureBundle ならそのまま返す。
    """
    if bundle_like is None:
        # 最低限のダミー
        ctx = FeatureContext(symbol="USDJPY", timeframe="M15")  # type: ignore
        return FeatureBundle(features={}, trace_id=_uuid(), context=ctx)  # type: ignore

    # そのまま使えるケース
    if hasattr(bundle_like, "context") and hasattr(bundle_like, "trace_id"):
        return bundle_like  # type: ignore[return-value]

    # dict 等 → FeatureBundle 再構築
    data = _to_dict(bundle_like)
    context = data.get("context") or {}
    if not isinstance(context, dict):
        context = _to_dict(context)

    symbol = context.get("symbol", "USDJPY")
    timeframe = context.get("timeframe", "M15")
    ctx = FeatureContext(symbol=symbol, timeframe=timeframe, **{k: v for k, v in context.items() if k not in {"symbol", "timeframe"}})  # type: ignore

    feats = data.get("features", data.get("feats", {})) or {}
    trace_id = data.get("trace_id") or _uuid()
    return FeatureBundle(features=feats, trace_id=trace_id, context=ctx)  # type: ignore


# =========================
# メインブリッジ
# =========================
def run_inventor_and_decide(
    fb: Any,
    conn_str: Optional[str] = None,
    use_harmonia: bool = True,
) -> Dict[str, Any]:
    """
    Airflow から呼び出されるブリッジ関数。
    - FeatureBundle を受け取り、Inventor で候補生成
    - （あれば）Harmonia.rerank_candidates で軽リランク
    - DecisionEngine で意思決定
    - 返却は Airflow/XCom フレンドリーな軽量 dict
    """
    bundle: FeatureBundle = _ensure_bundle(fb)
    trace_id = _get(bundle, "trace_id", None) or _uuid()

    # --- 候補生成 ---
    proposals: List[Any] = generate_proposals(bundle)  # StrategyProposal*(pydantic) の配列想定

    # --- Harmonia で軽リランク（存在すれば） ---
    if use_harmonia:
        try:
            from codex.agents.harmonia import rerank_candidates  # type: ignore

            ctx = _to_dict(_get(bundle, "context", {}))
            # 品質特徴（あれば）：missing_ratio / data_lag_min 等
            quality = {}
            feats = _get(bundle, "features", {}) or {}
            if isinstance(feats, dict):
                # 典型キーを拾う（無ければ空でOK）
                quality = {
                    k: v
                    for k, v in feats.items()
                    if k in {"missing_ratio", "data_lag_min", "data_lag", "data_lag_sec", "data_lag_minute"}
                }
            proposals = list(rerank_candidates(proposals, context=ctx, quality=quality))
        except Exception as e:
            log.info("[Harmonia] Rerank skipped or failed: %r", e)

    # --- 意思決定 ---
    eng = DecisionEngine()
    record, decision = eng.decide(bundle, proposals=proposals, conn_str=conn_str)

    # Airflow/XCom 返却用に dict 化
    d = decision if isinstance(decision, dict) else _to_dict(decision)

    # 非ゼロ size フォールバック（返り値上の利便性向上。DecisionEngine 内のログはそのまま）
    _fallback_size(d, proposals)

    return {
        "trace_id": trace_id,
        "proposal_summary": _summarize_proposals(proposals, k=10),
        "decision": d,
    }


__all__ = ["run_inventor_and_decide"]
