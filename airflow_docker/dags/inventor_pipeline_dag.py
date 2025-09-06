# airflow_docker/dags/inventor_pipeline_dag.py
from __future__ import annotations
from airflow.decorators import dag, task
from airflow.hooks.base import BaseHook
from datetime import datetime, timedelta

default_args = {
    "owner": "noctria",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

@dag(
    dag_id="inventor_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule="@hourly",
    catchup=False,
    default_args=default_args,
    tags=["noctria", "inventor", "plan"],
)
def inventor_pipeline():
    @task
    def fetch_features() -> dict:
        # 重い依存は関数内 import
        import pandas as pd
        # 実運用では S3/DB 置きの URI を返す方針。ここでは最小の context のみ。
        ctx = {
            "symbol": "USDJPY",
            "timeframe": "1h",
            "data_lag_min": 0,
            "missing_ratio": 0.02,
        }
        return {"context": ctx}

    @task
    def quality_gate(features: dict) -> dict:
        from plan_data.contracts import FeatureBundle  # 遅延 import
        from plan_data.quality_gate import evaluate_quality

        fb = FeatureBundle(df=None, context=features["context"])
        q = evaluate_quality(fb, conn_str=None)
        return {
            "context": features["context"],
            "quality": {
                "ok": q.ok,
                "action": q.action,
                "qty_scale": q.qty_scale,
                "reasons": q.reasons,
                "missing_ratio": q.missing_ratio,
                "data_lag_min": q.data_lag_min,
            },
        }

    @task
    def decide(features_with_qg: dict) -> dict:
        from plan_data.contracts import FeatureBundle
        from plan_data.run_inventor import run_inventor_and_decide

        # Airflow Connection（任意）。無ければ None
        try:
            conn = BaseHook.get_connection("noctria_db")
            conn_str = conn.get_uri()
        except Exception:
            conn_str = None

        fb = FeatureBundle(df=None, context=features_with_qg["context"])
        out = run_inventor_and_decide(fb, conn_str=conn_str, use_harmonia=True)
        # Quality 情報を tail に付与（GUI でまとめて見れるように）
        out["quality"] = features_with_qg.get("quality", {})
        return out

    # 依存定義
    ctx = fetch_features()
    qg = quality_gate(ctx)
    result = decide(qg)

inventor_pipeline()
