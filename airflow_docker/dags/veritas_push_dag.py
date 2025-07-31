from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("airflow.task")

def trigger_veritas_push(**context):
    dag_run = context.get("dag_run")
    conf = getattr(dag_run, "conf", {}) or {}
    strategy_name = conf.get("strategy_name", "default_strategy")
    decision_id = conf.get("decision_id", "NO_DECISION_ID")
    reason = conf.get("reason", "理由未指定")
    caller = conf.get("caller", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # バリデーション（王API経由のみ許可）
    if decision_id == "NO_DECISION_ID":
        logger.error("統治ID（decision_id）が指定されていません！王API経由のみ許可")
        raise ValueError("decision_idが必要です。Noctria王API経由でのみDAG起動が許可されます。")

    logger.info(f"🚀 [decision_id:{decision_id}] Starting GitHub push for strategy: {strategy_name} at {timestamp} / 呼出元: {caller} / 理由: {reason}")

    # --- GitHub push ロジック ---
    # 例: GitPythonで実装
    # import git
    # repo_path = "/opt/airflow/strategies/veritas_generated"
    # repo = git.Repo(repo_path)
    # repo.git.add(A=True)
    # repo.index.commit(f"[decision_id:{decision_id}] [AutoPush] Strategy pushed: {strategy_name} / 理由: {reason} / caller: {caller}")
    # repo.remote().push()
    # --- または外部スクリプト実行も同様にdecision_id/理由/callerを引数で渡す ---

    logger.info(f"✅ [decision_id:{decision_id}] Strategy '{strategy_name}' pushed successfully by {caller}.")

default_args = {
    "start_date": days_ago(1),
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="veritas_push_dag",
    description="PDCA戦略をGitHubにPushするDAG（統治ID・理由・呼出元必須）",
    schedule_interval=None,
    default_args=default_args,
    catchup=False,
    tags=["veritas", "strategy", "push"]
) as dag:

    push_task = PythonOperator(
        task_id="trigger_veritas_push",
        python_callable=trigger_veritas_push,
        provide_context=True
    )

    push_task
