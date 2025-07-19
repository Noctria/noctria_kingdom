# dags/veritas_generate_dag.py

from datetime import datetime
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
import os

# ================================================
# ★ 修正: 新しいimportルールを適用
# ================================================
# ロジックは外部モジュールに分離し、DAGはそれらを呼び出すだけ
from core.logger import setup_logger
from core.path_config import LOGS_DIR

# 専門家（ロジック担当）を召喚
from veritas.strategy_generator import build_prompt, generate_strategy_code, save_to_db, save_to_file
from tools.git_handler import push_to_github

# ================================================
# 🏰 王国記録係（DAGロガー）の召喚
# ================================================
dag_log_path = LOGS_DIR / "dags" / "veritas_generate_dag.log"
logger = setup_logger("VeritasGenerateDAG", dag_log_path)

# ================================================
# 📝 タスク定義
# ================================================
def _generate_and_save_task(**kwargs):
    """戦略を生成し、DBとファイルに保存するタスク"""
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    logger.info(f"📜 DAG実行コンフィグ: {conf}")

    # 1. プロンプト生成
    symbol = conf.get("symbol", "USDJPY")
    tag = conf.get("tag", "default")
    target_metric = conf.get("target_metric", "sharpe_ratio")
    prompt = build_prompt(symbol, tag, target_metric)

    # 2. LLMによる戦略コード生成
    generated_code = generate_strategy_code(prompt)

    # 3. 結果をDBに保存
    save_to_db(prompt, generated_code)

    # 4. コードをファイルに保存し、ファイルパスを次のタスクに渡す (XCom)
    file_path = save_to_file(generated_code, tag)
    return file_path

def _push_to_github_task(**kwargs):
    """前のタスクからファイルパスを受け取り、GitHubにPushするタスク"""
    ti = kwargs["ti"]
    file_path_to_push = ti.xcom_pull(task_ids="generate_and_save_strategy", key="return_value")
    
    if not file_path_to_push:
        logger.warning("⚠️ Pushするファイルがありません。前のタスクがファイルパスを返さなかった可能性があります。")
        return

    commit_message = f"🤖 Veritas戦略自動生成: {os.path.basename(file_path_to_push)}"
    push_to_github(file_path=file_path_to_push, commit_message=commit_message)

# ================================================
# 📜 DAG定義
# ================================================
with DAG(
    dag_id='veritas_generate_dag',
    default_args={'owner': 'Noctria', 'start_date': datetime(2025, 6, 1)},
    schedule_interval=None,
    catchup=False,
    tags=["veritas", "llm", "generator"]
) as dag:

    generate_task = PythonOperator(
        task_id="generate_and_save_strategy",
        python_callable=_generate_and_save_task
    )

    push_task = PythonOperator(
        task_id="push_strategy_to_github",
        python_callable=_push_to_github_task
    )

    generate_task >> push_task
