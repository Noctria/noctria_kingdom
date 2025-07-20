# airflow_docker/dags/aurus_strategy_dag.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# --- 各戦略AIのPythonモジュール名とクラス名をここで指定！ ---
STRATEGY_MODULE = "strategies.aurus_singularis"
STRATEGY_CLASS = "AurusSingularis"
DAG_ID = "aurus_strategy_dag"
DESCRIPTION = "⚔️ Noctria Kingdomの戦術官Aurusによるトレンド解析DAG"

default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description=DESCRIPTION,
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'trend-analysis'],
)

def trigger_task(**kwargs):
    ti = kwargs['ti']
    # --- テスト用ダミーデータ、用途に応じて修正可 ---
    mock_market_data = {
        "price": 1.2345,
        "volume": 500,
        "sentiment": 0.7,
        "trend_strength": 0.5,
        "volatility": 0.12,
        "order_block": 0.3,
        "momentum": 0.8,
        "trend_prediction": "bullish",
        "liquidity_ratio": 1.1,
    }
    ti.xcom_push(key='market_data', value=mock_market_data)

def strategy_task(**kwargs):
    ti = kwargs['ti']
    input_data = ti.xcom_pull(task_ids='trigger_task', key='market_data')

    if not input_data:
        input_data = {k: 0.0 for k in [
            "price", "volume", "sentiment", "trend_strength", "volatility",
            "order_block", "momentum", "trend_prediction", "liquidity_ratio"
        ]}
    try:
        # --- モジュール・クラスを変数から動的import ---
        import importlib
        strategy_module = importlib.import_module(STRATEGY_MODULE)
        StrategyClass = getattr(strategy_module, STRATEGY_CLASS)
        strategy = StrategyClass()
        decision = strategy.propose(input_data)
        ti.xcom_push(key='strategy_decision', value=decision)
        print(f"🔮 {STRATEGY_CLASS}の戦略判断: {decision}")
    except Exception as e:
        print(f"❌ {STRATEGY_CLASS}戦略中にエラー発生: {e}")

with dag:
    t1 = PythonOperator(
        task_id='trigger_task',
        python_callable=trigger_task,
    )
    t2 = PythonOperator(
        task_id='strategy_analysis_task',
        python_callable=strategy_task,
    )
    t1 >> t2
