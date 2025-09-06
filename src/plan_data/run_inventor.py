# src/plan_data/run_inventor.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# 遅延 import は呼び出し側(DAG)からこの関数が呼ばれた時点で行う
# DAGパース時に重い import を避けるため top-level では最小限のみ

def _import_feature_bundle():
    """
    FeatureBundle (pydantic v2) のインポート互換。
    プロジェクト内の配置差異に対応する。
    """
    try:
        from src.plan_data.contracts import FeatureBundle  # 推奨: alias of FeatureBundleV1
        return FeatureBundle
    except Exception:
        # フォールバック（環境差吸収用）
        from src.plan_data.feature_bundle import FeatureBundle  # type: ignore
        return FeatureBundle


def _to_feature_bundle(fb_like: Any):
    """
    dict / pydantic BaseModel / dataclass いずれでも FeatureBundle に正規化する。
    必須: features, trace_id
    任意: context（存在すればそのまま渡す）
    """
    FeatureBundle = _import_feature_bundle()

    # 既に正しい型（pydantic BaseModel）ならそのまま返す
    # pydantic v2 では model_dump を持つことが多い
    if hasattr(fb_like, "model_dump") and hasattr(fb_like, "features"):
        return fb_like

    # 属性型（dataclass/普通のクラス）
    if hasattr(fb_like, "features") and hasattr(fb_like, "trace_id"):
        ctx = getattr(fb_like, "context", None)
        return FeatureBundle(features=fb_like.features, trace_id=fb_like.trace_id, context=ctx)

    # dict型
    if isinstance(fb_like, dict):
        feats = fb_like.get("features")
        trace_id = fb_like.get("trace_id")
        ctx = fb_like.get("context")
        if feats is None or trace_id is None:
            raise ValueError("FeatureBundle requires 'features' and 'trace_id'.")
        return FeatureBundle(features=feats, trace_id=trace_id, context=ctx)

    # それ以外は未対応
    raise TypeError(f"Unsupported FeatureBundle-like object: {type(fb_like)}")


def _summarize_proposals(proposals: List[Dict[str, Any]], k: int = 10) -> List[Dict[str, Any]]:
    """
    XCom膨張を避けるため、上位K件のみ軽量要約を返す。
    'id' / 'score' / 'title' / 'reason' など代表的キーを拾う。
    """
    summary = []
    for p in proposals[:k]:
        summary.append({
            "id": p.get("id"),
            "score": p.get("score"),
            "title": p.get("title") or p.get("name"),
            "reason": p.get("reason"),
        })
    return summary


def run_inventor_and_decide(
    fb: Any,
    conn_str: str | None = None,
    use_harmonia: bool = True,
) -> Dict[str, Any]:
    """
    Inventor → (Harmonia) → DecisionEngine を橋渡しするエントリポイント。
    - fb: dict / FeatureBundle / dataclass いずれでもOK（内部で正規化）
    - conn_str: 観測ログ用（NOCTRIA_OBS_MODE=stdout なら None でもOK）
    - use_harmonia: True の場合、存在すれば rerank_candidates を適用

    Returns (XCom安全な軽量dict):
      {
        "trace_id": "...",
        "proposal_summary": [ {id, score, title, reason} ... ],
        "decision": {...},
      }
    """
    # 遅延 import（重い依存を避ける）
    from src.plan_data.inventor import generate_proposals  # 候補生成（plan層の純粋関数）
    from src.decision.decision_engine import DecisionEngine  # 決定エンジン

    # fb を必ず FeatureBundle に正規化
    bundle = _to_feature_bundle(fb)
    trace_id = getattr(bundle, "trace_id", None) or "N/A"

    # 1) 候補生成
    proposals: List[Dict[str, Any]] = generate_proposals(bundle)

    # 2) （任意）Harmonia rerank
    if use_harmonia:
        try:
            # 例: codex.agents.harmonia.rerank_candidates(proposals, bundle) を想定
            from codex.agents.harmonia import rerank_candidates  # type: ignore
            proposals = rerank_candidates(proposals, bundle) or proposals
        except Exception as e:
            # Rerank が未実装／失敗してもパイプラインは続行（LOW アラート相当）
            # ベストエフォート運用（XCom・DB膨張を避けて軽いログのみ）
            print(f"[Harmonia] Rerank skipped or failed: {e!r}")

    # 3) 決定
    eng = DecisionEngine()
    record, decision = eng.decide(bundle, proposals=proposals, conn_str=conn_str)

    # 4) 返却（XCom安全な軽量dictに限定）
    return {
        "trace_id": trace_id,
        "proposal_summary": _summarize_proposals(proposals, k=10),
        "decision": decision if isinstance(decision, dict) else getattr(decision, "model_dump", lambda: decision)(),
    }
