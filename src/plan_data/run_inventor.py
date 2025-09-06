# src/plan_data/run_inventor.py
from __future__ import annotations

from typing import Any, Dict, List


# ---------- internal helpers ----------

def _import_feature_bundle():
    """
    FeatureBundle (pydantic v2) のインポート互換。
    プロジェクト内配置差異に対応するため contracts 優先・フォールバックあり。
    """
    try:
        from src.plan_data.contracts import FeatureBundle  # 推奨: alias of FeatureBundleV1
        return FeatureBundle
    except Exception:
        from src.plan_data.feature_bundle import FeatureBundle  # type: ignore
        return FeatureBundle


def _to_feature_bundle(fb_like: Any):
    """
    dict / pydantic BaseModel / dataclass いずれでも FeatureBundle に正規化する。
    必須: features, trace_id
    任意: context
    """
    FeatureBundle = _import_feature_bundle()

    # pydantic v2 BaseModel らしきもの（model_dump を持つ & .features 属性あり）
    if hasattr(fb_like, "model_dump") and hasattr(fb_like, "features"):
        return fb_like

    # 属性型（dataclass/通常クラス）
    if hasattr(fb_like, "features") and hasattr(fb_like, "trace_id"):
        ctx = getattr(fb_like, "context", None)
        return FeatureBundle(features=fb_like.features, trace_id=fb_like.trace_id, context=ctx)

    # dict 型
    if isinstance(fb_like, dict):
        feats = fb_like.get("features")
        trace_id = fb_like.get("trace_id")
        ctx = fb_like.get("context")
        if feats is None or trace_id is None:
            raise ValueError("FeatureBundle requires 'features' and 'trace_id'.")
        return FeatureBundle(features=feats, trace_id=trace_id, context=ctx)

    raise TypeError(f"Unsupported FeatureBundle-like object: {type(fb_like)}")


def _to_plain_dict(obj: Any) -> Dict[str, Any]:
    """
    pydantic BaseModel / dict / 属性オブジェクトを防御的に dict 化。
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()  # pydantic v2
        except Exception:
            pass
    try:
        # よく使うキーを優先的に拾う（存在すれば）
        keys = ("strategy", "intent", "trace_id", "qty_raw", "score", "id")
        return {k: getattr(obj, k) for k in keys if hasattr(obj, k)}
    except Exception:
        return {}


def _summarize_proposals(proposals: List[Any], k: int = 10) -> List[Dict[str, Any]]:
    """
    proposals が pydantic BaseModel / dict / 混在でも落ちない要約器。
    StrategyProposalV1 最小スキーマ: {strategy: str, intent: Literal, trace_id: str, qty_raw?: float}
    """
    out: List[Dict[str, Any]] = []
    for p in proposals[:k]:
        d = _to_plain_dict(p)
        out.append({
            "strategy": d.get("strategy"),
            "intent": d.get("intent"),
            "qty": d.get("qty_raw"),
            "score": d.get("score"),
            "id": d.get("id"),
        })
    return out


def _decision_to_dict(decision: Any) -> Dict[str, Any]:
    """
    DecisionEngine の戻り値が pydantic / dict / クラスいずれでも JSON化。
    """
    if decision is None:
        return {}
    if isinstance(decision, dict):
        return decision
    if hasattr(decision, "model_dump") and callable(getattr(decision, "model_dump")):
        try:
            return decision.model_dump()
        except Exception:
            pass
    # 最後の手段（代表的フィールドだけ抜く）
    return _to_plain_dict(decision)


# ---------- public entrypoint ----------

def run_inventor_and_decide(
    fb: Any,
    conn_str: str | None = None,
    use_harmonia: bool = True,
) -> Dict[str, Any]:
    """
    Inventor → (Harmonia) → DecisionEngine の橋渡し。
    - fb: dict / FeatureBundle / dataclass いずれでもOK（内部で正規化）
    - conn_str: 観測ログ用（NOCTRIA_OBS_MODE=stdout なら None でもOK）
    - use_harmonia: True の場合、存在すれば rerank_candidates を適用

    Returns (XCom安全な軽量dict):
      {
        "trace_id": "...",
        "proposal_summary": [ {strategy, intent, qty, score?, id?} ... ],
        "decision": {...},
      }
    """
    # 遅延 import（DAG パース時に重い依存を避ける）
    from src.plan_data.inventor import generate_proposals
    from src.decision.decision_engine import DecisionEngine

    # 1) FeatureBundle へ正規化
    bundle = _to_feature_bundle(fb)
    trace_id = getattr(bundle, "trace_id", None) or "N/A"

    # 2) 候補生成（Inventor）
    proposals: List[Any] = generate_proposals(bundle)

    # 3) （任意）Harmonia rerank
    if use_harmonia:
        try:
            # 例: codex.agents.harmonia.rerank_candidates(proposals, bundle)
            from codex.agents.harmonia import rerank_candidates  # type: ignore
            new_props = rerank_candidates(proposals, bundle)
            if new_props:
                proposals = new_props
        except Exception as e:
            # 未実装や失敗は LOW 扱い（処理は継続）
            print(f"[Harmonia] Rerank skipped or failed: {e!r}")

    # 4) 決定（DecisionEngine）
    eng = DecisionEngine()
    record, decision = eng.decide(bundle, proposals=proposals, conn_str=conn_str)

    # 5) 返却（XCom向け軽量）
    return {
        "trace_id": trace_id,
        "proposal_summary": _summarize_proposals(proposals, k=10),
        "decision": _decision_to_dict(decision),
    }
