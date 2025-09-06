# airflow_docker/dags/inventor_pipeline_dag.py
from __future__ import annotations

from datetime import datetime, timedelta
import uuid
from typing import Any, Dict

from airflow import DAG
from airflow.decorators import task


default_args = {
    "owner": "noctria",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def _qres_to_dict(obj: Any) -> Dict[str, Any]:
    """
    QualityResult / pydantic BaseModel / dataclass / dict のいずれにも対応して
    {passed, reason, details} を取り出すユーティリティ。
    未提供フィールドは安全なデフォルトを補う。
    """
    if obj is None:
        return {"passed": True, "reason": "", "details": {}}

    # pydantic v2 BaseModel 互換
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        d = obj.model_dump()
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
    # details が dict でない場合の保険
    if not isinstance(details, dict):
        details = {"details": details}
    return {"passed": bool(passed), "reason": reason, "details": details}


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
        XCom 膨張を避けるため軽量 dict のみを返す。
        context は FeatureBundleV1 のスキーマ（extra=forbid）に合わせて最小限。
        """
        trace_id = str(uuid.uuid4())

        # ✅ 必須最小 context
        context = {
            "symbol": "USDJPY",   # 必須
            "timeframe": "M15",   # 必須（必要に応じて変更可）
        }

        # ✅ 品質ゲートで使う値は context ではなく features に置く
        features = {
            "bias": 1.0,
            "missing_ratio": 0.02,  # quality_gate で参照するならここに
        }

        return {"trace_id": trace_id, "features": features, "context": context}

    @task
    def quality_gate(payload: dict) -> dict:
        """
        FeatureBundleV1 の必須: features, trace_id（+ 任意 context）で構築し、
        evaluate_quality の結果（QualityResult など）を防御的に dict 化して返す。
        """
        # 遅延 import（DAG パース時に重い import を避ける）
        from src.plan_data.quality_gate import evaluate_quality  # 実プロジェクト名に合わせる
        try:
            # 推奨の契約モデル
            from src.plan_data.contracts import FeatureBundle  # = FeatureBundleV1
        except Exception:
            # フォールバック（環境差対応）
            from src.plan_data.feature_bundle import FeatureBundle  # 例

        trace_id = payload["trace_id"]
        feats = payload["features"]

        # ✅ context は必須キーのみ（extra=forbid対策）
        ctx_in = payload.get("context") or {}
        ctx = {"symbol": ctx_in["symbol"], "timeframe": ctx_in["timeframe"]}

        # pydantic v2: extra=forbid の想定。df など余計なキーは渡さない
        fb = FeatureBundle(features=feats, trace_id=trace_id, context=ctx)

        # 実装に合わせて関数名を調整（evaluate_quality / evaluate / run 等）
        qres = evaluate_quality(fb)
        qd = _qres_to_dict(qres)

        return {
            "trace_id": trace_id,
            "passed": qd["passed"],
            "reason": qd["reason"],
            "details": qd["details"],
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

        out = _run(
            fb={
                "trace_id": payload["trace_id"],
                "features": payload["features"],
                "context": payload.get("context", {}),
            },
            conn_str=None,     # NOCTRIA_OBS_MODE=stdout で DB 不要運用可能
            use_harmonia=True, # rerank 未実装なら内部で LOW アラート & スキップ
        )
        # out 例: {"trace_id": "...", "proposal_summary": [...], "decision": {...}}
        return out

    # DAG wiring
    features = collect_features()
    gated = quality_gate(features)
    _ = run_inventor_and_decide(gated)
