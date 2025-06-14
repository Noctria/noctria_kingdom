# /opt/airflow/dags/noctria_kingdom_dag.py

import sys
sys.path.append('/opt/airflow')  # Airflow環境でcore/やstrategies/を認識させる

from core.logger import setup_logger  # ✅ ログ機能
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

from strategies.aurus_singularis import AurusSingularis
from strategies.levia_tempest import LeviaTempest
from strategies.noctus_sentinella import NoctusSentinella
from strategies.prometheus_oracle import PrometheusOracle
from core.noctria import Noctria

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

# === 各AIタスク ===

def aurus_task(**context):
    logger = setup_logger("NoctriaDecision")
    try:
        aurus = AurusSingularis()
        decision = aurus.process({"trend_strength": 0.6})

        if decision is None:
            logger.warning("[Aurus] decision is None")
        elif decision not in ["BUY", "SELL", "HOLD"]:
            logger.warning(f"[Aurus] unexpected decision: {decision}")

        logger.info(f"[Aurus] decision: {decision}")
        context['ti'].xcom_push(key='aurus_decision', value=decision)
    except Exception as e:
        logger.error(f"[Aurus] exception occurred: {e}")

def levia_task(**context):
    logger = setup_logger("NoctriaDecision")
    try:
        levia = LeviaTempest()
        decision = levia.process({"price": 1.25, "spread": 0.01})

        if decision is None:
            logger.warning("[Levia] decision is None")
        elif decision not in ["BUY", "SELL", "HOLD"]:
            logger.warning(f"[Levia] unexpected decision: {decision}")

        logger.info(f"[Levia] decision: {decision}")
        context['ti'].xcom_push(key='levia_decision', value=decision)
    except Exception as e:
        logger.error(f"[Levia] exception occurred: {e}")

def noctus_task(**context):
    logger = setup_logger("NoctriaDecision")
    try:
        noctus = NoctusSentinella()
        decision = noctus.process({"volume": 130, "spread": 0.012, "volatility": 0.2})

        if decision is None:
            logger.warning("[Noctus] decision is None")
        elif decision not in ["RISK_ON", "RISK_OFF", "MAINTAIN_POSITION"]:
            logger.warning(f"[Noctus] unexpected decision: {decision}")

        logger.info(f"[Noctus] decision: {decision}")
        context['ti'].xcom_push(key='noctus_decision', value=decision)
    except Exception as e:
        logger.error(f"[Noctus] exception occurred: {e}")

def prometheus_task(**context):
    logger = setup_logger("NoctriaDecision")
    try:
        prometheus = PrometheusOracle()
        decision = prometheus.process({"macro_score": 0.75})

        if decision is None:
            logger.warning("[Prometheus] decision is None")
        elif decision not in ["BUY", "SELL", "HOLD"]:
            logger.warning(f"[Prometheus] unexpected decision: {decision}")

        logger.info(f"[Prometheus] decision: {decision}")
        context['ti'].xcom_push(key='prometheus_decision', value=decision)
    except Exception as e:
        logger.error(f"[Prometheus] exception occurred: {e}")

# === 王Noctriaが全てを統合するタスク ===

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

# === DAGタスク定義 ===

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

    [t1, t2, t3, t4] >> t5
