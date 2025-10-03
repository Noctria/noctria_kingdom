# [NOCTRIA_CORE_REQUIRED]
# airflow_docker/dags/noctria_kingdom_pdca_dag.py
# 変更点:
# ① sys.pathハック削除
# ② importを src. プレフィックスへ
# ③ get_current_context() を各タスク内で使用（Airflow 2系推奨）
# ④ provide_context は未使用（不要）
# ⑤ conf/params を optimize_main に「そのまま」渡すよう修正（→ study_name/env_id 等が反映される）
# ⑥ best選定は best_value と minimize フラグで判断（max/min 切替）
# ⑦ schedule_interval → schedule（非推奨解消）
# ⑧ 解析時worker数は“DAG定義時”の既定で固定（実行時confで変えるのは不可なため）。選定側は confのworker_countを上限に考慮
# ⑨ 各主要タスク終了時に log_event() でDBロギング
# ⑩ royal_decision_task を拡張：昇格済みモデルパスをXCom/メタから解決し、NOCTRIA_MODEL_PATH として渡す
# ⑪ 追記（本マージで追加）: pdca_start で trace_id を起票し XCom 伝搬、observability をグレースフル統合

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from airflow.models.dag import DAG

try:
    from airflow.operators.python import PythonOperator, get_current_context
except Exception:
    # かなり古い環境向けフォールバック
    from airflow.operators.python_operator import (  # type: ignore
        PythonOperator,
        get_current_context,  # type: ignore
    )

from src.core.db_logging import log_event
from src.core.logger import setup_logger
from src.core.path_config import LOGS_DIR

# --- 追加: 安全な import path ブートストラップ（存在すれば呼び出し） -----------------
try:
    from src.core.path_config import ensure_import_path  # type: ignore

    ensure_import_path()
except Exception:
    pass

# --- 追加: observability / trace はグレースフルに扱う --------------------------------
try:
    from src.plan_data import observability as obs  # type: ignore
except Exception:
    obs = None  # type: ignore

try:
    from src.plan_data import trace as trace_mod  # type: ignore
except Exception:
    trace_mod = None  # type: ignore

from src.scripts.apply_best_params_to_kingdom import apply_best_params_to_kingdom
from src.scripts.apply_best_params_to_metaai import apply_best_params_to_metaai
from src.scripts.optimize_params_with_optuna import optimize_main

dag_log_path = LOGS_DIR / "dags" / "noctria_kingdom_pdca_dag.log"
logger = setup_logger("NoctriaPDCA_DAG", dag_log_path)


def task_failure_alert(context):
    # 必要に応じて失敗通知（Slack/メール等）を実装
    pass


default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": task_failure_alert,
}


# --- 追加: 観測ログの薄いラッパ（obs 優先、失敗時は STDOUT JSON） -------------------
def _obs_log(
    level: str, msg: str, *, extra: Dict[str, Any] | None = None, trace_id: str | None = None
) -> None:
    extra = extra or {}
    try:
        if obs is not None:
            if level == "info":
                obs.log_info(msg, extra=extra, trace_id=trace_id)  # type: ignore[attr-defined]
            elif level in ("warn", "warning"):
                obs.log_warn(msg, extra=extra, trace_id=trace_id)  # type: ignore[attr-defined]
            elif level == "error":
                obs.log_error(msg, extra=extra, trace_id=trace_id)  # type: ignore[attr-defined]
            else:
                obs.log_debug(msg, extra=extra, trace_id=trace_id)  # type: ignore[attr-defined]
            return
    except Exception:
        # fallthrough to stdout
        pass

    print(
        json.dumps(
            {
                "ts": datetime.utcnow().isoformat(),
                "level": level.upper(),
                "msg": msg,
                "trace_id": trace_id,
                "extra": extra,
            },
            ensure_ascii=False,
        )
    )


def _new_trace_id() -> str:
    try:
        if trace_mod is not None and hasattr(trace_mod, "new_trace_id"):
            return trace_mod.new_trace_id()  # type: ignore[attr-defined]
    except Exception:
        pass
    return f"trace-{datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')}"


def _conf_reason() -> str:
    ctx = get_current_context()
    dr = ctx.get("dag_run")
    if not dr:
        return "理由未指定"
    conf = dr.conf or {}
    return conf.get("reason", "理由未指定")


# DAG定義
with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="Optuna→MetaAI→Kingdom→Royal Decision のPDCA統合",
    schedule="@daily",  # ← schedule_interval は非推奨
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca", "metaai", "royal"],
    # ※ DAG定義時の既定。実行時 conf で値は参照できるが、タスク数など“構造”は変えられない点に注意
    params={"worker_count": 3, "n_trials": 100},
) as dag:
    # DAG定義時の worker 数（構造はここで固定）
    _DEFAULT_WORKER_COUNT = int(dag.params.get("worker_count", 3))

    # --------- 追加: trace_id 起票タスク（全体の親） ---------
    def pdca_start_task(**kwargs):
        trace_id = _new_trace_id()
        reason = _conf_reason()
        _obs_log("info", "PDCA start", extra={"reason": reason}, trace_id=trace_id)

        # 監査ログ
        try:
            log_event(
                table="pdca_events",
                event_type="PDCA_START",
                payload={"reason": reason, "trace_id": trace_id},
            )
        except Exception as e:
            logger.warning(f"log_event 失敗（PDCA_START）: {e}")

        # XCom へ
        ctx = get_current_context()
        ctx["ti"].xcom_push(key="trace_id", value=trace_id)
        return {"trace_id": trace_id, "reason": reason}

    pdca_start = PythonOperator(
        task_id="pdca_start",
        python_callable=pdca_start_task,
    )

    # --------- タスク定義 ---------
    def optimize_worker_task(worker_id: int, **kwargs):
        """
        最適化ワーカー。optimize_main に "contextをそのまま" 渡すのが重要。
        → optimize_main 側で params/env を解釈し、study_name/env_id などが正しく反映される。
        """
        ctx = get_current_context()
        ti = ctx["ti"]
        trace_id = ti.xcom_pull(task_ids="pdca_start", key="trace_id") or _new_trace_id()

        logger.info(f"【実行理由】worker_{worker_id}: {_conf_reason()}")
        _obs_log("info", "Optuna worker start", extra={"worker_id": worker_id}, trace_id=trace_id)

        # optimize_main は **context を受け取る設計
        result: Dict[str, Any] = optimize_main(**ctx)  # ← ここが肝

        if not result or "best_params" not in result:
            logger.warning(f"worker_{worker_id}: 最適化結果なし（result={result}）")
            _obs_log(
                "warn", "Optimize result empty", extra={"worker_id": worker_id}, trace_id=trace_id
            )
            return None

        # 監査ログ
        try:
            log_event(
                table="pdca_events",
                event_type="OPTIMIZE_COMPLETED",
                payload={
                    "trace_id": trace_id,
                    "worker_id": worker_id,
                    "reason": _conf_reason(),
                    "result": {
                        "study_name": result.get("study_name"),
                        "best_value": result.get("best_value"),
                        "best_params": result.get("best_params"),
                        "n_trials": result.get("n_trials"),
                        "worker_tag": result.get("worker_tag"),
                    },
                },
            )
        except Exception as e:
            logger.warning(f"log_event 失敗（OPTIMIZE_COMPLETED）: {e}")

        _obs_log("info", "Optuna worker done", extra={"worker_id": worker_id}, trace_id=trace_id)
        return result

    def select_best_params_task(**kwargs):
        """
        各ワーカーの結果（result dict）から best_value を用いてベストを選定。
        minimize が True の場合は最小値、それ以外は最大値。
        """
        ctx = get_current_context()
        ti = ctx["ti"]
        trace_id = ti.xcom_pull(task_ids="pdca_start", key="trace_id") or _new_trace_id()

        # 実行時 conf の worker_count（多くても構造上の上限 _DEFAULT_WORKER_COUNT まで）
        conf_wc = (
            int((ctx.get("dag_run").conf or {}).get("worker_count", _DEFAULT_WORKER_COUNT))
            if ctx.get("dag_run")
            else _DEFAULT_WORKER_COUNT
        )
        use_wc = min(conf_wc, _DEFAULT_WORKER_COUNT)

        logger.info(f"【選定理由】{_conf_reason()} / use_workers={use_wc}")
        _obs_log("info", "Selecting best params", extra={"use_workers": use_wc}, trace_id=trace_id)

        results: List[Optional[Dict[str, Any]]] = [
            ti.xcom_pull(task_ids=f"optimize_worker_{i}") for i in range(1, use_wc + 1)
        ]
        results = [r for r in results if r and "best_value" in r and "best_params" in r]

        if not results:
            logger.warning("全ワーカー結果が空")
            _obs_log("warn", "No worker results", trace_id=trace_id)
            return None

        # minimize（実行時 conf or params）で選定基準切替
        params = (
            (ctx.get("dag_run").conf or {}) if ctx.get("dag_run") else (ctx.get("params") or {})
        )
        minimize = bool(str(params.get("minimize", "false")).lower() in ("1", "true", "yes"))

        keyfunc = (
            (lambda r: r.get("best_value", float("inf")))
            if minimize
            else (lambda r: r.get("best_value", float("-inf")))
        )
        best = min(results, key=keyfunc) if minimize else max(results, key=keyfunc)

        # 後段タスク用に best_params をキー付きで渡す（互換維持）
        ti.xcom_push(key="best_params", value=best.get("best_params"))
        ti.xcom_push(key="best_result", value=best)

        try:
            log_event(
                table="pdca_events",
                event_type="BEST_PARAMS_SELECTED",
                payload={"best_result": best, "reason": _conf_reason(), "trace_id": trace_id},
            )
        except Exception as e:
            logger.warning(f"log_event 失敗（BEST_PARAMS_SELECTED）: {e}")

        _obs_log("info", "Best params selected", trace_id=trace_id)
        return best

    def apply_metaai_task(**kwargs):
        """
        選定された best_params を MetaAI に反映。
        """
        ctx = get_current_context()
        ti = ctx["ti"]
        trace_id = ti.xcom_pull(task_ids="pdca_start", key="trace_id") or _new_trace_id()

        best_params = ti.xcom_pull(key="best_params", task_ids="select_best_params")
        logger.info(f"【MetaAI適用理由】{_conf_reason()}")
        _obs_log("info", "Applying best params to MetaAI", trace_id=trace_id)

        if not best_params:
            logger.warning("ベストパラメータなし")
            _obs_log("warn", "No best params", trace_id=trace_id)
            return None

        result = apply_best_params_to_metaai(best_params=best_params)

        try:
            log_event(
                table="pdca_events",
                event_type="META_AI_APPLIED",
                payload={
                    "best_params": best_params,
                    "result": result,
                    "reason": _conf_reason(),
                    "trace_id": trace_id,
                },
            )
        except Exception as e:
            logger.warning(f"log_event 失敗（META_AI_APPLIED）: {e}")

        _obs_log("info", "MetaAI apply done", trace_id=trace_id)
        return result

    def apply_kingdom_task(**kwargs):
        """
        MetaAI に適用されたモデルを Kingdom（本番）へ昇格。
        """
        ctx = get_current_context()
        trace_id = ctx["ti"].xcom_pull(task_ids="pdca_start", key="trace_id") or _new_trace_id()

        model_info = ctx["ti"].xcom_pull(task_ids="apply_best_params_to_metaai")
        logger.info(f"【Kingdom昇格理由】{_conf_reason()}")
        _obs_log("info", "Promoting model to Kingdom", trace_id=trace_id)

        if not model_info:
            logger.warning("モデル情報なし")
            _obs_log("warn", "No model_info", trace_id=trace_id)
            return None

        result = apply_best_params_to_kingdom(model_info=model_info)

        try:
            log_event(
                table="pdca_events",
                event_type="KINGDOM_PROMOTED",
                payload={
                    "model_info": model_info,
                    "result": result,
                    "reason": _conf_reason(),
                    "trace_id": trace_id,
                },
            )
        except Exception as e:
            logger.warning(f"log_event 失敗（KINGDOM_PROMOTED）: {e}")

        _obs_log("info", "Kingdom promotion done", trace_id=trace_id)
        return result

    def royal_decision_task(**kwargs):
        """
        王の最終決断（取引実行など）。
        直前の昇格結果（XCom）または production メタから本番モデルパスを解決し、
        NOCTRIA_MODEL_PATH として渡してから Noctria().execute_trade() を実行。
        """
        logger.info(f"【王決断理由】{_conf_reason()}")
        ctx = get_current_context()
        ti = ctx["ti"]
        trace_id = ti.xcom_pull(task_ids="pdca_start", key="trace_id") or _new_trace_id()
        _obs_log("info", "Royal decision start", trace_id=trace_id)

        # productionメタのパス規約（apply_best_params_to_kingdom.py と合わせる）
        MODELS_DIR = Path(os.environ.get("NOCTRIA_MODELS_DIR", "/opt/airflow/data/models"))
        PRODUCTION_DIR = Path(
            os.environ.get("NOCTRIA_PRODUCTION_DIR", str(MODELS_DIR / "production"))
        )
        META_NAME = os.environ.get(
            "NOCTRIA_PRODUCTION_META_NAME", "metaai_production_metadata.json"
        )
        META_PATH = PRODUCTION_DIR / META_NAME

        # まずは直前のXCom（apply_best_params_to_kingdom の戻り値）から
        model_info = ti.xcom_pull(task_ids="apply_best_params_to_kingdom")
        prod_path = None
        if isinstance(model_info, dict):
            prod_path = model_info.get("production_model_path") or model_info.get("model_path")

        # 取れなければ production メタから復元
        if not prod_path and META_PATH.exists():
            try:
                with META_PATH.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
                prod_path = meta.get("model_path")
            except Exception as e:
                logger.warning(f"productionメタ読み取り失敗: {e}")
                _obs_log(
                    "warn",
                    "Read production meta failed",
                    extra={"error": str(e)},
                    trace_id=trace_id,
                )

        # 解決できなければスキップ
        if not prod_path:
            logger.warning("productionモデルパスが取得できませんでした（スキップ）")
            _obs_log("warn", "No production model path", trace_id=trace_id)
            return {"status": "skipped", "reason": "no production model", "trace_id": trace_id}

        # 環境変数で Noctria へ受け渡し
        os.environ["NOCTRIA_MODEL_PATH"] = str(prod_path)
        logger.info(f"王決断に使用するモデル: {prod_path}")
        _obs_log(
            "info",
            "Set NOCTRIA_MODEL_PATH",
            extra={"model_path": str(prod_path)},
            trace_id=trace_id,
        )

        from src.noctria_ai.noctria import Noctria

        try:
            result = Noctria().execute_trade()
            try:
                log_event(
                    table="pdca_events",
                    event_type="ROYAL_DECISION",
                    payload={
                        "result": result,
                        "reason": _conf_reason(),
                        "model_path": str(prod_path),
                        "trace_id": trace_id,
                    },
                )
            except Exception as e:
                logger.warning(f"log_event 失敗（ROYAL_DECISION）: {e}")
            _obs_log("info", "Royal decision done", trace_id=trace_id)
            return result
        except Exception as e:
            logger.error(f"王決断で例外: {e}")
            try:
                log_event(
                    table="pdca_events",
                    event_type="ROYAL_DECISION_ERROR",
                    payload={
                        "error": str(e),
                        "reason": _conf_reason(),
                        "model_path": str(prod_path),
                        "trace_id": trace_id,
                    },
                )
            except Exception as e2:
                logger.warning(f"log_event 失敗（ROYAL_DECISION_ERROR）: {e2}")
            _obs_log("error", "Royal decision error", extra={"error": str(e)}, trace_id=trace_id)
            return {"status": "error", "message": str(e), "trace_id": trace_id}

    # --------- タスク組み立て ---------
    workers = [
        PythonOperator(
            task_id=f"optimize_worker_{i}",
            python_callable=optimize_worker_task,
            op_kwargs={"worker_id": i},
        )
        for i in range(1, _DEFAULT_WORKER_COUNT + 1)
    ]

    select_best = PythonOperator(
        task_id="select_best_params",
        python_callable=select_best_params_task,
    )
    apply_metaai = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=apply_metaai_task,
    )
    apply_kingdom = PythonOperator(
        task_id="apply_best_params_to_kingdom",
        python_callable=apply_kingdom_task,
    )
    royal_decision = PythonOperator(
        task_id="royal_decision",
        python_callable=royal_decision_task,
    )

    # 依存関係（trace_id を確実に伝搬するため、全ワーカーの前段に pdca_start）
    pdca_start >> workers
    workers >> select_best >> apply_metaai >> apply_kingdom >> royal_decision
