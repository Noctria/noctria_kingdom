from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import subprocess
import logging

default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    dag_id='veritas_ollama_dag',
    default_args=default_args,
    description='Veritas_MachinaがOllama(OpenHermes)に戦略プロンプトを送信するDAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['veritas', 'ollama', 'llm'],
)

def run_veritas_test_script():
    log = logging.getLogger("airflow.task")
    
    # ✅ Dockerマウントされている実パス
    script_path = '/noctria_kingdom/airflow_docker/scripts/test_ollama_veritas.py'
    
    log.info(f"📜 Veritas スクリプト実行: {script_path}")
    result = subprocess.run(['python3', script_path], capture_output=True, text=True)

    log.info("📤 STDOUT:\n" + result.stdout)
    log.info("⚠️ STDERR:\n" + result.stderr)

    if result.returncode != 0:
        raise RuntimeError("❌ Veritas テストスクリプト実行中にエラーが発生しました")

run_veritas = PythonOperator(
    task_id='veritas_ollama_prompt',
    python_callable=run_veritas_test_script,
    dag=dag,
)
