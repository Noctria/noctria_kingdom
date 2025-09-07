# airflow_docker/dags/inventor_pipeline_dag.py
from __future__ import annotations

from datetime import datetime, timedelta
import uuid
from typing import Any, Dict

from airflow import DAG
from airflow.decorators import task, get_current_context

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
#  - dag_run.conf によるパラメータ化に対応（symbol / timeframe / bias / missing_ratio 等）
#  - XCom は軽量 dict のみを返す
#  - run_inventor_and_decide() へは bundle=... で渡す（fb ではなく）
# =============================================================================
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

        # ✅ 品質ゲートで使う値は context ではなく features に置く（conf で上書き可）
        features = {
            "bias": float(conf.get("bias", 1.0)),
            "missing_ratio": float(conf.get("missing_ratio", 0.02)),
            # 追加の軽量特徴があればここに記載
        }

        # 参考：quality_gate で data_lag_min を使いたい場合は conf から拾って context 側で持つ
        data_lag_min = conf.get("data_lag_min", None)
        if data_lag_min is not None:
            try:
                context["data_lag_min"] = float(data_lag_min)
            except Exception:
                # 無効値は無視（extra=forbid のため最終的には弾く）
                pass

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
            use_model = True
        except Exception:
            # venvや依存差分へのフォールバック: 素の dict で渡す
            FeatureBundle = dict  # type: ignore
            use_model = False

        trace_id = payload["trace_id"]
        feats = payload["features"]

        # ✅ context は必須キーのみ（extra=forbid対策）
        ctx_in = payload.get("context") or {}
        # 許容キー以外は削って最小化
        ctx_min: Dict[str, Any] = {
            "symbol": ctx_in["symbol"],
            "timeframe": ctx_in["timeframe"],
        }
        # data_lag_min を使う運用なら、contracts 側で許容されている前提で条件付きで付与
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

        # NOTE:
        #   run_inventor_and_decide() は bundle=... を受け取る想定。
        #   以前の fb=... だと無視されるため、ここで bundle=... に統一。
        out = _run(
            bundle={
                "context": payload.get("context", {}),
                # features は現状 Decision 直結では未使用だが、将来のために含めてOK
                "features": payload.get("features", {}),
                "trace_id": payload.get("trace_id"),
            },
            # 成果物保存を使いたい場合はパスを渡す（例：codex_reports/inventor_last.json）
            # artifact_path="codex_reports/inventor_last.json",
        )
        # out 例: {"trace_id": "...", "context": {...}, "decision": {...}, "meta": {...}}
        return out

    # DAG wiring
    features = collect_features()
    gated = quality_gate(features)
    _ = run_inventor_and_decide(gated)
