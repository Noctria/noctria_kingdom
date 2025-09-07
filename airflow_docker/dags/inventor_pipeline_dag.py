# airflow_docker/dags/inventor_pipeline_dag.py
from __future__ import annotations

from datetime import datetime, timedelta
import uuid
from typing import Any, Dict

from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import get_current_context  # ← ここがポイント

# =============================================================================
# 共通ユーティリティ
# =============================================================================
default_args = {
    "owner": "noctria",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def _qres_to_dict(obj: Any) -> Dict[str, Any]:
    """
    QualityResult / pydantic BaseModel(v1/v2) / dataclass / dict を許容して
    {passed, reason, details} を抽出するユーティリティ。
    未提供フィールドは安全なデフォルトを補う。
    """
    if obj is None:
        return {"passed": True, "reason": "", "details": {}}

    # pydantic v2 BaseModel
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        d = obj.model_dump()
        return {
            "passed": bool(d.get("passed", True)),
            "reason": d.get("reason", "") or "",
            "details": d.get("details", {}) or {},
        }

    # pydantic v1 BaseModel
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        d = obj.dict()
        return {
            "passed": bool(d.get("passed", True)),
            "reason": d.get("reason", "") or "",
            "details": d.get("details", {}) or {},
        }

    # dict 互換
    if isinstance(obj, dict):
        return {
            "passed": bool(obj.get("passed", True)),
            "reason": obj.get("reason", "") or "",
            "details": obj.get("details", {}) or {},
        }

    # 属性アクセス（dataclass / 普通のクラス）
    passed = getattr(obj, "passed", True)
    reason = getattr(obj, "reason", "") or ""
    details = getattr(obj, "details", {}) or {}
    if not isinstance(details, dict):
        details = {"details": details}
    return {"passed": bool(passed), "reason": reason, "details": details}


# =============================================================================
# DAG 本体
# =============================================================================
with DAG(
    dag_id="inventor_pipeline",
    description="Inventor → (Harmonia) → DecisionEngine minimal pipeline",
    start_date=datetime(2025, 9, 1),
    schedule_interval=None,        # ← Airflow互換のため schedule_interval を使用
    catchup=False,
    default_args=default_args,
    tags=["noctria", "inventor", "harmonia", "decision"],
) as dag:

    @task
    def collect_features() -> dict:
        """
        XCom 膨張を避けるため軽量 dict のみを返す。
        dag_run.conf から symbol/timeframe/bias/missing_ratio を受け取って上書き可能。
        """
        ctx = get_current_context()
        conf = (ctx.get("dag_run") or {}).conf or {}

        trace_id = str(uuid.uuid4())

        # ✅ 必須最小 context（dag_run.conf で上書き可）
        context = {
            "symbol": conf.get("symbol", "USDJPY"),
            "timeframe": conf.get("timeframe", "M15"),
        }

        # ✅ 品質ゲートで使う値は features に置く（conf で上書き可）
        features = {
            "bias": float(conf.get("bias", 1.0)),
            "missing_ratio": float(conf.get("missing_ratio", 0.02)),
        }

        # 参考: quality_gate で data_lag_min を使うなら conf から拾って context へ
        if "data_lag_min" in conf:
            try:
                context["data_lag_min"] = float(conf["data_lag_min"])
            except Exception:
                pass

        return {"trace_id": trace_id, "features": features, "context": context}

    @task
    def quality_gate(payload: dict) -> dict:
        """
        FeatureBundleV1 の必須: features, trace_id（+ 任意 context）で構築し、
        evaluate_quality の結果を防御的に dict 化して返す。
        """
        # 遅延 import（DAG パース時の重依存回避）
        from src.plan_data.quality_gate import evaluate_quality  # 実プロジェクト名に合わせる
        try:
            from src.plan_data.contracts import FeatureBundle  # = FeatureBundleV1
            use_model = True
        except Exception:
            FeatureBundle = dict  # type: ignore
            use_model = False

        trace_id = payload["trace_id"]
        feats = payload["features"]

        # extra=forbid 対策で context を最小化
        ctx_in = payload.get("context") or {}
        ctx_min: Dict[str, Any] = {
            "symbol": ctx_in["symbol"],
            "timeframe": ctx_in["timeframe"],
        }
        if "data_lag_min" in ctx_in:
            ctx_min["data_lag_min"] = ctx_in["data_lag_min"]

        fb = (
            FeatureBundle(features=feats, trace_id=trace_id, context=ctx_min)
            if use_model
            else {"features": feats, "trace_id": trace_id, "context": ctx_min}
        )

        qres = evaluate_quality(fb)
        qd = _qres_to_dict(qres)

        return {
            "trace_id": trace_id,
            "passed": qd["passed"],
            "reason": qd["reason"],
            "details": qd["details"],
            "features": feats,
            "context": ctx_min,
        }

    @task
    def run_inventor_and_decide(payload: dict) -> dict:
        """
        Inventor → (Harmonia) → Decision の橋渡し。
        XCom には軽い dict のみを返す。
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
            bundle={
                "context": payload.get("context", {}),
                "features": payload.get("features", {}),
                "trace_id": payload.get("trace_id"),
            },
            # artifact_path="codex_reports/inventor_last.json",  # 必要なら有効化
        )
        return out

    # DAG wiring
    features = collect_features()
    gated = quality_gate(features)
    _ = run_inventor_and_decide(gated)
