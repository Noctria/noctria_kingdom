# airflow_docker/dags/aurus_strategy_dag.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

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
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【Aurusトリガータスク・発令理由】{reason}")

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
        "trigger_reason": reason,  # 理由もデータに記録
    }
    ti.xcom_push(key='market_data', value=mock_market_data)

def strategy_task(**kwargs):
    ti = kwargs['ti']
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【Aurus解析タスク・発令理由】{reason}")

    input_data = ti.xcom_pull(task_ids='trigger_task', key='market_data')

    if not input_data:
        input_data = {k: 0.0 for k in [
            "price", "volume", "sentiment", "trend_strength", "volatility",
            "order_block", "momentum", "trend_prediction", "liquidity_ratio"
        ]}
    try:
        import importlib
        strategy_module = importlib.import_module(STRATEGY_MODULE)
        StrategyClass = getattr(strategy_module, STRATEGY_CLASS)
        strategy = StrategyClass()
        decision = strategy.propose(input_data)
        # 発令理由も決定内容に残す
        result = {"decision": decision, "reason": reason}
        ti.xcom_push(key='strategy_decision', value=result)
        print(f"🔮 {STRATEGY_CLASS}の戦略判断: {result}")
    except Exception as e:
        print(f"❌ {STRATEGY_CLASS}戦略中にエラー発生: {e}")

with dag:
    t1 = PythonOperator(
        task_id='trigger_task',
        python_callable=trigger_task,
        provide_context=True
    )
    t2 = PythonOperator(
        task_id='strategy_analysis_task',
        python_callable=strategy_task,
        provide_context=True
    )
    t1 >> t2
