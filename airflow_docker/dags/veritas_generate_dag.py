from datetime import datetime, timedelta
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
import os
import logging

from core.logger import setup_logger
from core.path_config import LOGS_DIR

from veritas.strategy_generator import build_prompt, generate_strategy_code, save_to_db, save_to_file

# ロガー設定
dag_log_path = LOGS_DIR / "dags" / "veritas_generate_dag.log"
logger = setup_logger("VeritasGenerateDAG", dag_log_path)

def _generate_and_save_task(**kwargs):
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    logger.info(f"📜 DAG実行コンフィグ: {conf}（発令理由: {reason}）")

    try:
        symbol = conf.get("symbol", "USDJPY")
        tag = conf.get("tag", "default")
        target_metric = conf.get("target_metric", "sharpe_ratio")
        prompt = build_prompt(symbol, tag, target_metric)
        logger.info(f"📝 プロンプト生成完了: {prompt[:100]}...")

        generated_code = generate_strategy_code(prompt)
        logger.info(f"🧠 戦略コード生成完了。コード長: {len(generated_code)}")

        save_to_db(prompt, generated_code)
        logger.info(f"💾 DB保存完了。")

        file_path = save_to_file(generated_code, tag)
        logger.info(f"📂 ファイル保存完了: {file_path}")

        ti = kwargs["ti"]
        ti.xcom_push(key="trigger_reason", value=reason)
        return str(file_path)

    except Exception as e:
        logger.error(f"❌ 戦略生成処理中にエラー発生: {e}", exc_info=True)
        raise

def _push_to_github_task(**kwargs):
    import subprocess
    # airflow_docker/dags/ 配下からの相対パスを構築（適宜修正してください）
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "scripts", "push_generated_strategy.py")
    try:
        subprocess.run(["python3", script_path], check=True)
        logger.info("✅ GitHubへのPushが完了しました。")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ GitHub Push中にエラー発生: {e}", exc_info=True)
        raise

with DAG(
    dag_id='veritas_generate_dag',
    default_args={
        'owner': 'Noctria',
        'start_date': datetime(2025, 6, 1),
        'retries': 3,
        'retry_delay': timedelta(minutes=5),
    },
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "ml", "generator"]
) as dag:

    generate_task = PythonOperator(
        task_id="generate_and_save_strategy",
        python_callable=_generate_and_save_task,
        provide_context=True,
    )

    push_task = PythonOperator(
        task_id="push_strategy_to_github",
        python_callable=_push_to_github_task,
        provide_context=True,
    )

    generate_task >> push_task
