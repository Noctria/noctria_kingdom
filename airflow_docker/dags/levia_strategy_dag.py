import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# ✅ Noctria Kingdom v2.0 パス管理
from core.path_config import STRATEGIES_DIR

# ✅ コンテナ環境用PYTHONPATHに追加（Airflow Worker用）
sys.path.append(str(STRATEGIES_DIR))

# ✅ DAG共通設定
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

# === Veritasからのデータ注入（模擬） ===
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

# === Leviaによるスキャルピング判断 ===
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
        from levia_tempest import LeviaTempest  # STRATEGIES_DIR に配置されている前提
        levia = LeviaTempest()
        decision = levia.process(input_data)

        ti.xcom_push(key='levia_decision', value=decision)
        print(f"⚔️ Levia: 『王よ、我が刃はこの刻、{decision}に振るうと見定めました。』")

    except Exception as e:
        print(f"❌ Levia戦略中にエラー発生: {e}")
        raise

# === DAGタスク構成（Airflow司令官） ===
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
