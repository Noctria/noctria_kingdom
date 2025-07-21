# airflow_docker/dags/hermes_strategy_dag.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

STRATEGY_MODULE = "strategies.hermes_cognitor"
STRATEGY_CLASS = "HermesCognitorStrategy"
DAG_ID = "hermes_strategy_dag"
DESCRIPTION = "🦉 Noctria Kingdomの言語大臣Hermes Cognitorによる説明生成DAG"

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
    schedule_interval=None,  # 必要に応じて「@daily」など自動化
    start_date=datetime(2025, 7, 21),
    catchup=False,
    tags=['noctria', 'llm', 'explanation'],
)

def trigger_task(**kwargs):
    ti = kwargs['ti']
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【Hermesトリガータスク・発令理由】{reason}")

    # ここでは説明生成の元ネタ（特徴量・要因ラベルなど）をダミーで用意
    mock_features = {
        "win_rate": 75.2,
        "max_drawdown": -4.1,
        "news_count": 18,
        "fomc_today": True,
        "risk": "low"
    }
    mock_labels = [
        "勝率が良好です",
        "リスク水準が低下しています",
        "今日はFOMCイベント日です"
    ]
    # 発令理由も記録
    ti.xcom_push(key='llm_features', value=mock_features)
    ti.xcom_push(key='llm_labels', value=mock_labels)
    ti.xcom_push(key='trigger_reason', value=reason)

def hermes_strategy_task(**kwargs):
    ti = kwargs['ti']
    conf = kwargs.get("dag_run").conf if kwargs.get("dag_run") else {}
    reason = conf.get("reason", "理由未指定")
    print(f"【Hermes解析タスク・発令理由】{reason}")

    features = ti.xcom_pull(task_ids='trigger_task', key='llm_features')
    labels = ti.xcom_pull(task_ids='trigger_task', key='llm_labels')

    if not features or not labels:
        features = {}
        labels = []

    try:
        import importlib
        strategy_module = importlib.import_module(STRATEGY_MODULE)
        StrategyClass = getattr(strategy_module, STRATEGY_CLASS)
        strategy = StrategyClass()
        # LLMによる説明生成（ここはダミー or 本実装可）
        explanation = strategy.summarize_strategy(features, labels)
        result = {"explanation": explanation, "reason": reason}
        ti.xcom_push(key='hermes_explanation', value=result)
        print(f"🦉 Hermesの説明生成結果: {result}")
    except Exception as e:
        print(f"❌ {STRATEGY_CLASS}実行中にエラー発生: {e}")

with dag:
    t1 = PythonOperator(
        task_id='trigger_task',
        python_callable=trigger_task,
        provide_context=True
    )
    t2 = PythonOperator(
        task_id='hermes_strategy_task',
        python_callable=hermes_strategy_task,
        provide_context=True
    )
    t1 >> t2
