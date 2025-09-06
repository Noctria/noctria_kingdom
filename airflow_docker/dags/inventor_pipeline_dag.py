# airflow_docker/dags/inventor_pipeline_dag.py
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
    schedule=None,  # manual trigger
    catchup=False,
    default_args=default_args,
    tags=["noctria", "inventor", "harmonia", "decision"],
) as dag:

    @task
    def collect_features() -> dict:
        """
        軽量な特徴量ダミー＋コンテキスト＋trace_id を返す。
        XCom を肥大化させないため、最小限の dict に限定。
        """
        # 遅延 import（DAG パース時に重い import を避ける）
        # 実際は collector などから取るが、ここでは最小ダミー
        trace_id = str(uuid.uuid4())
        features = {
            # ここに実際の特徴量 key/value を詰める（最小例）
            "bias": 1.0,
        }
        context = {
            "missing_ratio": 0.02,
            "data_lag": 0,
        }
        return {"trace_id": trace_id, "features": features, "context": context}

    @task
    def quality_gate(payload: dict) -> dict:
        """
        Quality Gate を通過させる。pydantic FeatureBundleV1 に適合する形で渡す。
        必須: features, trace_id / 任意: context
        """
        # 遅延 import
        from src.plan_data.quality_gate import evaluate_quality  # 想定API名
        try:
            from src.plan_data.contracts import FeatureBundle  # pydantic model (alias of FeatureBundleV1)
        except Exception:
            # 一部プロジェクトでは contracts の場所が異なる場合があるためフォールバック
            from src.plan_data.feature_bundle import FeatureBundle  # 例: 互換パス

        # payload から正しく取り出す
        trace_id = payload["trace_id"]
        feats = payload["features"]
        ctx = payload.get("context", {})

        # ❌ df は渡さない（pydantic が extra=forbid）
        fb = FeatureBundle(features=feats, trace_id=trace_id, context=ctx)

        # evaluate が FeatureBundle を受ける前提
        # 戻り値は { "passed": bool, "reason": str, "details": dict } を想定
        result = evaluate_quality(fb)

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
        Inventor → (Harmonia) → DecisionEngine の橋渡し。
        XComには軽い dict のみ返す。
        """
        # 遅延 import（重い依存を避ける）
        from src.plan_data.run_inventor import run_inventor_and_decide as _run

        # quality_gate を通っていない/失敗は安全側でアラートしてスキップ or セーフ動作
        if not payload.get("passed", True):
            # ここで軽いアラート（実装側が emit_alert を内包していれば不要）
            # ただし、このタスクでは失敗させずにスキップ扱いの結果を返す
            return {
                "trace_id": payload.get("trace_id"),
                "skipped": True,
                "reason": f"quality_gate not passed: {payload.get('reason')}",
                "details": payload.get("details", {}),
            }

        # run_inventor_and_decide は FeatureBundle ではなく「軽量dictインタフェース」対応にしておく
        out = _run(
            fb={
                "trace_id": payload["trace_id"],
                "features": payload["features"],
                "context": payload.get("context", {}),
            },
            conn_str=None,          # NOCTRIA_OBS_MODE=stdout であればDBなくてもOK
            use_harmonia=True,      # rerank が無ければ内部で LOW アラート & スキップ
        )
        # out 例: {"trace_id": "...", "proposal_summary": [...], "decision": {...}}
        return out

    # DAG wiring
    features = collect_features()
    gated = quality_gate(features)
    _ = run_inventor_and_decide(gated)
