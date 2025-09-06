from __future__ import annotations

from datetime import datetime, timedelta
import uuid

from airflow import DAG
from airflow.decorators import task

default_args = {
    "owner": "noctria",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="inventor_pipeline",
    description="Inventor → (Harmonia) → DecisionEngine minimal pipeline",
    start_date=datetime(2025, 9, 1),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["noctria", "inventor", "harmonia", "decision"],
) as dag:

    @task
    def collect_features() -> dict:
        """
        XCom膨張を避けるため軽量dictのみ。
        context は FeatureBundleV1 のスキーマに厳密に合わせる（extra=forbid 対策）。
        """
        trace_id = str(uuid.uuid4())
        # ✅ 必須最小 context
        context = {
            "symbol": "USDJPY",   # 必須
            "timeframe": "M15",   # 必須（必要なら "H1" 等に変更可）
        }
        # ✅ features に品質ゲートの元ネタを寄せる（contextに入れない）
        features = {
            "bias": 1.0,
            "missing_ratio": 0.02,  # ← quality gateで参照するならこちらに
        }
        return {"trace_id": trace_id, "features": features, "context": context}

    @task
    def quality_gate(payload: dict) -> dict:
        """
        FeatureBundleV1 の必須: features, trace_id（+ 任意 context）で構築。
        """
        # 遅延 import（DAGパース時に重いimport回避）
        from src.plan_data.quality_gate import evaluate_quality  # 実装名に合わせて
        try:
            from src.plan_data.contracts import FeatureBundle  # = FeatureBundleV1
        except Exception:
            from src.plan_data.feature_bundle import FeatureBundle  # フォールバック例

        trace_id = payload["trace_id"]
        feats = payload["features"]
        # ✅ contextは必須フィールドのみを厳守（unknownを入れない）
        ctx_in = payload.get("context") or {}
        ctx = {"symbol": ctx_in["symbol"], "timeframe": ctx_in["timeframe"]}

        fb = FeatureBundle(features=feats, trace_id=trace_id, context=ctx)
        result = evaluate_quality(fb)  # 期待: {"passed": bool, "reason": str, "details": dict}

        return {
            "trace_id": trace_id,
            "passed": bool(result.get("passed", True)),
            "reason": result.get("reason", ""),
            "details": result.get("details", {}),
            "features": feats,
            "context": ctx,
        }

    @task
    def run_inventor_and_decide(payload: dict) -> dict:
        """
        Inventor → (Harmonia) → DecisionEngine。XComは軽量dict。
        """
        from src.plan_data.run_inventor import run_inventor_and_decide as _run

        if not payload.get("passed", True):
            return {
                "trace_id": payload.get("trace_id"),
                "skipped": True,
                "reason": f"quality_gate not passed: {payload.get('reason')}",
                "details": payload.get("details", {}),
            }

        out = _run(
            fb={
                "trace_id": payload["trace_id"],
                "features": payload["features"],
                "context": payload.get("context", {}),
            },
            conn_str=None,     # NOCTRIA_OBS_MODE=stdout ならDB不要で可
            use_harmonia=True, # Rerank未実装なら内部でLOWアラート & スキップ
        )
        return out

    features = collect_features()
    gated = quality_gate(features)
    _ = run_inventor_and_decide(gated)
