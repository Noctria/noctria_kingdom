# /opt/airflow/dags/noctria_kingdom_dag.py

import sys
sys.path.append('/opt/airflow')  # Airflowからcore/やstrategies/を認識させる

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

from core.logger import setup_logger
from core.noctria import Noctria
from strategies.aurus_singularis import AurusSingularis
from strategies.levia_tempest import LeviaTempest
from strategies.noctus_sentinella import NoctusSentinella
from strategies.prometheus_oracle import PrometheusOracle

# === DAG設定 ===
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='noctria_kingdom_dag',
    default_args=default_args,
    description='Noctria王国全体戦略統合DAG（XCom連携）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'kingdom'],
)

# === 各AIユニットのタスク定義 ===

def aurus_task(**context):
    logger = setup_logger("NoctriaDecision")
    try:
        aurus = AurusSingularis()
        decision = aurus.process({"trend_strength": 0.6})
        logger.info(f"[Aurus] decision: {decision}")
        context['ti'].xcom_push(key='aurus_decision', value=decision)
    except Exception as e:
        logger.error(f"[Aurus] exception occurred: {e}")

def levia_task(**context):
    logger = setup_logger("NoctriaDecision")
    try:
        levia = LeviaTempest()
        decision = levia.process({"price": 1.25, "spread": 0.01})
        logger.info(f"[Levia] decision: {decision}")
        context['ti'].xcom_push(key='levia_decision', value=decision)
    except Exception as e:
        logger.error(f"[Levia] exception occurred: {e}")

def noctus_task(**context):
    logger = setup_logger("NoctriaDecision")
    try:
        noctus = NoctusSentinella()
        decision = noctus.process({"volume": 130, "spread": 0.012, "volatility": 0.2})
        logger.info(f"[Noctus] decision: {decision}")
        context['ti'].xcom_push(key='noctus_decision', value=decision)
    except Exception as e:
        logger.error(f"[Noctus] exception occurred: {e}")

def prometheus_task(**context):
    logger = setup_logger("NoctriaDecision")
    try:
        prometheus = PrometheusOracle()
        decision = prometheus.process({"macro_score": 0.75})
        logger.info(f"[Prometheus] decision: {decision}")
        context['ti'].xcom_push(key='prometheus_decision', value=decision)
    except Exception as e:
        logger.error(f"[Prometheus] exception occurred: {e}")

# === 王Noctriaによる統合判断タスク ===

def noctria_final_decision(**context):
    logger = setup_logger("NoctriaDecision")
    ti = context['ti']
    decisions = {
        "Aurus": ti.xcom_pull(key='aurus_decision', task_ids='aurus_strategy'),
        "Levia": ti.xcom_pull(key='levia_decision', task_ids='levia_strategy'),
        "Noctus": ti.xcom_pull(key='noctus_decision', task_ids='noctus_strategy'),
        "Prometheus": ti.xcom_pull(key='prometheus_decision', task_ids='prometheus_strategy'),
    }

    logger.info(f"👑 王Noctriaが受け取った判断: {decisions}")
    noctria = Noctria()
    final_action = noctria.meta_ai.decide_final_action(decisions)
    logger.info(f"🏰 王国全体の最終戦略決定: {final_action}")

# === DAGにタスク登録 ===

with dag:
    t1 = PythonOperator(
        task_id='aurus_strategy',
        python_callable=aurus_task,
        provide_context=True,
    )
    t2 = PythonOperator(
        task_id='levia_strategy',
        python_callable=levia_task,
        provide_context=True,
    )
    t3 = PythonOperator(
        task_id='noctus_strategy',
        python_callable=noctus_task,
        provide_context=True,
    )
    t4 = PythonOperator(
        task_id='prometheus_strategy',
        python_callable=prometheus_task,
        provide_context=True,
    )
    t5 = PythonOperator(
        task_id='noctria_final_decision',
        python_callable=noctria_final_decision,
        provide_context=True,
    )

    # すべての戦略が終わった後に王Noctriaが判断
    [t1, t2, t3, t4] >> t5
