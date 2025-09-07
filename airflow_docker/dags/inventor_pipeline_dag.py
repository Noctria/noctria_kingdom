# airflow_docker/dags/inventor_pipeline_dag.py
from __future__ import annotations

from datetime import datetime, timedelta
import uuid
from typing import Any, Dict

from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable

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


with DAG(
    dag_id="inventor_pipeline",
    description="Inventor → (Harmonia) → DecisionEngine minimal pipeline",
    start_date=datetime(2025, 9, 1),
    schedule_interval=None,  # manual trigger
    catchup=False,
    default_args=default_args,
    tags=["noctria", "inventor", "harmonia", "decision"],
) as dag:

    @task
    def collect_features() -> dict:
        """
        XCom 膨張を避けるため軽量 dict のみを返す。
        dag_run.conf を取り込み、context/features に伝搬する。
        """
        trace_id = str(uuid.uuid4())

        # dag_run.conf の取り込み（Airflow 2系互換：get_current_context を安全に取得）
        try:
            from airflow.operators.python import get_current_context  # type: ignore
            conf: Dict[str, Any] = (get_current_context().get("dag_run").conf) or {}
        except Exception:
            conf = {}

        # ✅ 必須最小 context（conf で上書き可）
        symbol = str(conf.get("symbol") or "USDJPY")
        timeframe = str(conf.get("timeframe") or "M15")
        context = {"symbol": symbol, "timeframe": timeframe}

        # ✅ features 側に品質系を寄せる（conf を反映）
        features = {
            "bias": float(conf.get("bias", 1.0) or 1.0),
            "missing_ratio": float(conf.get("missing_ratio", 0.02) or 0.02),
            # data_lag_min は conf にあれば採用（なければ 0）
            "data_lag_min": float(conf.get("data_lag_min", 0.0) or 0.0),
        }

        return {"trace_id": trace_id, "features": features, "context": context}

    @task
    def quality_gate(payload: dict) -> dict:
        """
        FeatureBundleV1 の必須: features, trace_id（+ 任意 context）で構築し、
        evaluate_quality の結果（QualityResult など）を防御的に dict 化して返す。
        さらに、Airflow Variables のしきい値で通過/スキップを判定する。
        """
        # 遅延 import（DAG パース時に重い import を避ける）
        from src.plan_data.quality_gate import evaluate_quality  # 実プロジェクト名に合わせる
        try:
            # 推奨の契約モデル
            from src.plan_data.contracts import FeatureBundle  # = FeatureBundleV1
            use_model = True
        except Exception:
            FeatureBundle = dict  # type: ignore
            use_model = False

        trace_id = payload["trace_id"]
        feats = dict(payload["features"] or {})
        ctx_in = dict(payload.get("context") or {})
        ctx = {"symbol": str(ctx_in["symbol"]), "timeframe": str(ctx_in["timeframe"])}

        # pydantic v2: extra=forbid を想定。余計なキーは渡さない
        fb = FeatureBundle(features=feats, trace_id=trace_id, context=ctx) if use_model else {
            "features": feats,
            "trace_id": trace_id,
            "context": ctx,
        }

        # 実測（evaluate_quality から取得）
        qres = evaluate_quality(fb)
        qd = _qres_to_dict(qres)

        # ===== 運用しきい値（Airflow Variables） =====
        # デフォルトは緩め（運用で調整）
        try:
            miss_max = float(Variable.get("NOCTRIA_QG_MISSING_MAX", default_var="0.20"))
        except Exception:
            miss_max = 0.20
        try:
            lag_max_min = float(Variable.get("NOCTRIA_QG_LAG_MAX_MIN", default_var="10"))
        except Exception:
            lag_max_min = 10.0

        # 実測値の取り出し（details > features > 既定）
        details = dict(qd.get("details") or {})
        missing_ratio = float(details.get("missing_ratio", feats.get("missing_ratio", 0.0)) or 0.0)
        data_lag_min = float(details.get("data_lag_min", feats.get("data_lag_min", 0.0)) or 0.0)

        # しきい値チェック
        passed_threshold = (missing_ratio <= miss_max) and (data_lag_min <= lag_max_min)
        passed = bool(qd["passed"] and passed_threshold)
        reason = qd["reason"] or ""
        if not passed_threshold:
            lack = []
            if missing_ratio > miss_max:
                lack.append(f"missing_ratio {missing_ratio:.3f}>{miss_max:.3f}")
            if data_lag_min > lag_max_min:
                lack.append(f"data_lag_min {data_lag_min:.1f}>{lag_max_min:.1f}")
            reason = (reason + " | " if reason else "") + "quality_threshold_not_met: " + ", ".join(lack)

        # details に実測を明示
        details.update({"missing_ratio": missing_ratio, "data_lag_min": data_lag_min,
                        "thresholds": {"missing_max": miss_max, "lag_max_min": lag_max_min}})

        return {
            "trace_id": trace_id,
            "passed": passed,
            "reason": reason,
            "details": details,
            "features": feats,
            "context": ctx,
        }

    @task
    def run_inventor_and_decide(payload: dict) -> dict:
        """
        Inventor → (Harmonia) → DecisionEngine の橋渡し。
        XCom には軽い dict のみを返し、大きなデータは外部ストレージで参照。
        """
        # 遅延 import（重い依存を避ける）
        from src.plan_data.run_inventor import run_inventor_and_decide as _run

        # 品質ゲート未通過は安全側にスキップ（タスク自体は失敗させない）
        if not payload.get("passed", True):
            return {
                "trace_id": payload.get("trace_id"),
                "skipped": True,
                "reason": f"quality_gate not passed: {payload.get('reason')}",
                "details": payload.get("details", {}),
            }

        # 余計な kwargs は渡さない（将来の契約変更に強くする）
        out = _run(
            bundle={
                "trace_id": payload["trace_id"],
                "features": payload["features"],
                "context": payload.get("context", {}),
            },
            # ★ 毎回 artifact を固定パスに保存
            artifact_path="codex_reports/inventor_last.json",
        )
        return out

    # DAG wiring
    features = collect_features()
    gated = quality_gate(features)
    _ = run_inventor_and_decide(gated)
