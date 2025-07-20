# dags/veritas_generate_dag.py

from datetime import datetime
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
import os

from core.logger import setup_logger
from core.path_config import LOGS_DIR

from veritas.strategy_generator import build_prompt, generate_strategy_code, save_to_db, save_to_file
from tools.git_handler import push_to_github

dag_log_path = LOGS_DIR / "dags" / "veritas_generate_dag.log"
logger = setup_logger("VeritasGenerateDAG", dag_log_path)

def _generate_and_save_task(**kwargs):
    """戦略を生成し、DBとファイルに保存するタスク（理由付き）"""
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    logger.info(f"📜 DAG実行コンフィグ: {conf}（発令理由: {reason}）")

    # 1. プロンプト生成
    symbol = conf.get("symbol", "USDJPY")
    tag = conf.get("tag", "default")
    target_metric = conf.get("target_metric", "sharpe_ratio")
    prompt = build_prompt(symbol, tag, target_metric)

    # 2. LLMによる戦略コード生成
    generated_code = generate_strategy_code(prompt)

    # 3. 結果をDBに保存（理由も含めるならここでDB設計に追加）
    save_to_db(prompt, generated_code)

    # 4. コードをファイルに保存し、ファイルパス・発令理由をXComで次タスクに渡す
    file_path = save_to_file(generated_code, tag)
    ti = kwargs["ti"]
    ti.xcom_push(key="trigger_reason", value=reason)
    return file_path

def _push_to_github_task(**kwargs):
    ti = kwargs["ti"]
    file_path_to_push = ti.xcom_pull(task_ids="generate_and_save_strategy", key="return_value")
    reason = ti.xcom_pull(task_ids="generate_and_save_strategy", key="trigger_reason")
    if not file_path_to_push:
        logger.warning("⚠️ Pushするファイルがありません。前のタスクがファイルパスを返さなかった可能性があります。")
        return
    commit_message = f"🤖 Veritas戦略自動生成: {os.path.basename(file_path_to_push)}"
    if reason and reason != "理由未指定":
        commit_message += f"｜理由: {reason}"
    push_to_github(file_path=file_path_to_push, commit_message=commit_message)

with DAG(
    dag_id='veritas_generate_dag',
    default_args={'owner': 'Noctria', 'start_date': datetime(2025, 6, 1)},
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "llm", "generator"]
) as dag:

    generate_task = PythonOperator(
        task_id="generate_and_save_strategy",
        python_callable=_generate_and_save_task,
        provide_context=True
    )

    push_task = PythonOperator(
        task_id="push_strategy_to_github",
        python_callable=_push_to_github_task,
        provide_context=True
    )

    generate_task >> push_task
