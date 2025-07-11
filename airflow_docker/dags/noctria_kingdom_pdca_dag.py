# airflow_docker/dags/noctria_kingdom_pdca_dag.py

from datetime import datetime, timedelta
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# ================================
# ★ 修正: 新しいimportルールを適用
# ================================
# `PYTHONPATH`が設定されたため、sys.pathハックは不要。
# 全てのモジュールは、srcを起点とした絶対パスでインポートする。
from core.path_config import LOGS_DIR
from core.logger import setup_logger
from scripts.optimize_params_with_optuna import optimize_main
from scripts.apply_best_params_to_metaai import apply_best_params_to_metaai
from scripts.apply_best_params_to_kingdom import apply_best_params_to_kingdom

# ================================
# 🏰 王国記録係（DAGロガー）の召喚
# ================================
dag_log_path = LOGS_DIR / "dags" / "noctria_kingdom_pdca_dag.log"
logger = setup_logger("NoctriaPDCA_DAG", dag_log_path)

# ================================
# 🚨 失敗通知コールバック
# ================================
def task_failure_alert(context):
    """タスク失敗時にログを出力し、外部通知を行う（将来的にSlack等へ）"""
    failed_task = context.get('task_instance').task_id
    dag_name = context.get('dag').dag_id
    exec_date = context.get('execution_date')
    log_url = context.get('task_instance').log_url
    
    message = f"""
    🚨 Airflow Task Failed!
    - DAG: {dag_name}
    - Task: {failed_task}
    - Execution Date: {exec_date}
    - Log URL: {log_url}
    """
    logger.error(message)
    # ここにSlackやDiscordへの通知処理を実装する

# ================================
# 📜 王命: DAG共通設定
# ================================
default_args = {
    "owner": "Noctria",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": task_failure_alert,
}

# ================================
# 👑 王命: Noctria Kingdom 統合PDCAサイクル
# ================================
with DAG(
    dag_id="noctria_kingdom_pdca_dag",
    description="🏰 Noctria KingdomのPDCAサイクル統合DAG（Optuna最適化 → MetaAI再学習 → 王国戦略反映）",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "kingdom", "pdca", "metaai"],
    params={
        "n_trials": 100
    },
) as dag:

    # ================================
    # 📝 タスクラッパー関数（XComsとロギングを統合）
    # ================================
    def _optimize_task(**kwargs):
        # ... (この部分のロジックは変更なし) ...
        n_trials = kwargs["params"].get("n_trials", 100)
        logger.info(f"🎯 叡智の探求を開始します (試行回数: {n_trials})")
        best_params = optimize_main(n_trials=n_trials)
        if not best_params:
            raise ValueError("最適化タスクから有効なパラメータが返されませんでした。")
        logger.info(f"✅ 最適パラメータを発見: {best_params}")
        return best_params

    def _apply_metaai_task(**kwargs):
        # ... (この部分のロジックは変更なし) ...
        ti = kwargs["ti"]
        best_params = ti.xcom_pull(task_ids="optimize_with_optuna", key="return_value")
        logger.info(f"🧠 MetaAIへの叡智継承を開始します (パラメータ: {best_params})")
        # apply_best_params_to_metaaiは、モデルのパスとスコアを返すと仮定
        model_info = apply_best_params_to_metaai(best_params=best_params)
        logger.info(f"✅ MetaAIへの継承が完了しました: {model_info}")
        return model_info # 次のタスクへモデル情報を渡す

    def _apply_kingdom_task(**kwargs):
        # ... (この部分のロジックは変更なし) ...
        ti = kwargs["ti"]
        model_info = ti.xcom_pull(task_ids="apply_best_params_to_metaai", key="return_value")
        logger.info(f"⚔️ 王国戦略の制定を開始します (モデル情報: {model_info})")
        apply_best_params_to_kingdom(model_info=model_info)
        logger.info("✅ 王国戦略の制定が完了しました")

    # ================================
    # ⛓️ タスク定義と依存関係
    # ================================
    optimize_task = PythonOperator(
        task_id="optimize_with_optuna",
        python_callable=_optimize_task,
    )

    apply_metaai_task = PythonOperator(
        task_id="apply_best_params_to_metaai",
        python_callable=_apply_metaai_task,
    )

    apply_kingdom_task = PythonOperator(
        task_id="apply_best_params_to_kingdom",
        python_callable=_apply_kingdom_task,
    )

    optimize_task >> apply_metaai_task >> apply_kingdom_task
