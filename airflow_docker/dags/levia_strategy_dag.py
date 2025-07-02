import sys
sys.path.append('/opt/airflow')  # ✅ AirflowコンテナのPYTHONPATHを明示

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# ✅ 重いインポートはタスク関数内で実行する（後述）
# from strategies.levia_tempest import LeviaTempest ← DAG起動遅延の原因になる

# === DAG共通設定 ===
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='levia_strategy_dag',
    default_args=default_args,
    description='⚔️ Noctria Kingdomの風刃Leviaによるスキャルピング戦略DAG（XCom対応）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'scalping'],
)

# === Veritas等からのデータ注入タスク ===
def veritas_trigger_task(ti, **kwargs):
    mock_market_data = {
        "price": 1.2050,
        "previous_price": 1.2040,
        "volume": 150,
        "spread": 0.012,
        "order_block": 0.4,
        "volatility": 0.15
    }
    ti.xcom_push(key='market_data', value=mock_market_data)

# === Leviaによるスキャルピング判断タスク ===
def levia_strategy_task(ti, **kwargs):
    input_data = ti.xcom_pull(task_ids='veritas_trigger_task', key='market_data')

    if input_data is None:
        print("⚠️ market_dataが存在しません。デフォルトデータを使用します。")
        input_data = {
            "price": 1.0,
            "previous_price": 1.0,
            "volume": 100,
            "spread": 0.01,
            "order_block": 0.0,
            "volatility": 0.1
        }

    try:
        from strategies.levia_tempest import LeviaTempest
        levia = LeviaTempest()
        decision = levia.process(input_data)

        ti.xcom_push(key='levia_decision', value=decision)
        print(f"⚔️ Levia: 『王よ、我が刃はこの刻、{decision}に振るうと見定めました。』")

    except Exception as e:
        print(f"❌ Levia戦略中にエラー発生: {e}")
        raise

# === DAGへ登録 ===
with dag:
    veritas_task = PythonOperator(
        task_id='veritas_trigger_task',
        python_callable=veritas_trigger_task,
    )

    levia_task = PythonOperator(
        task_id='levia_scalping_task',
        python_callable=levia_strategy_task,
    )

    veritas_task >> levia_task
