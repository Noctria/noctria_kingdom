import sys
sys.path.append('/opt/airflow')  # Docker環境対応（必要に応じて）

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
    schedule_interval=None,  # 必要に応じて '@daily' などに変更
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'kingdom'],
)

# === 共通ロガー ===
logger = setup_logger("NoctriaDecision", "/noctria_kingdom/airflow_docker/logs/noctria_decision.log")

# === 各戦略AIタスク定義 ===
def aurus_task(**kwargs):
    try:
        decision = AurusSingularis().process({"trend_strength": 0.6})
        logger.info(f"[Aurus] decision: {decision}")
        kwargs['ti'].xcom_push(key='aurus_decision', value=decision)
    except Exception as e:
        logger.error(f"[Aurus] exception: {e}")

def levia_task(**kwargs):
    try:
        decision = LeviaTempest().process({"price": 1.25, "spread": 0.01})
        logger.info(f"[Levia] decision: {decision}")
        kwargs['ti'].xcom_push(key='levia_decision', value=decision)
    except Exception as e:
        logger.error(f"[Levia] exception: {e}")

def noctus_task(**kwargs):
    try:
        decision = NoctusSentinella().process({"volume": 130, "spread": 0.012, "volatility": 0.2})
        logger.info(f"[Noctus] decision: {decision}")
        kwargs['ti'].xcom_push(key='noctus_decision', value=decision)
    except Exception as e:
        logger.error(f"[Noctus] exception: {e}")

def prometheus_task(**kwargs):
    try:
        decision = PrometheusOracle().process({"macro_score": 0.75})
        logger.info(f"[Prometheus] decision: {decision}")
        kwargs['ti'].xcom_push(key='prometheus_decision', value=decision)
    except Exception as e:
        logger.error(f"[Prometheus] exception: {e}")

# === 王Noctriaの統合意思決定 ===
def noctria_final_decision(**kwargs):
    ti = kwargs['ti']
    decisions = {
        "Aurus": ti.xcom_pull(task_ids='aurus_strategy', key='aurus_decision'),
        "Levia": ti.xcom_pull(task_ids='levia_strategy', key='levia_decision'),
        "Noctus": ti.xcom_pull(task_ids='noctus_strategy', key='noctus_decision'),
        "Prometheus": ti.xcom_pull(task_ids='prometheus_strategy', key='prometheus_decision'),
    }
    logger.info(f"👑 王Noctriaが受け取った判断: {decisions}")
    noctria = Noctria()
    final_action = noctria.meta_ai.decide_final_action(decisions)
    logger.info(f"🏰 王国全体の最終戦略決定: {final_action}")

# === DAGへのタスク登録 ===
with dag:
    aurus_op = PythonOperator(task_id='aurus_strategy', python_callable=aurus_task)
    levia_op = PythonOperator(task_id='levia_strategy', python_callable=levia_task)
    noctus_op = PythonOperator(task_id='noctus_strategy', python_callable=noctus_task)
    prometheus_op = PythonOperator(task_id='prometheus_strategy', python_callable=prometheus_task)

    final_decision_op = PythonOperator(task_id='noctria_final_decision', python_callable=noctria_final_decision)

    [aurus_op, levia_op, noctus_op, prometheus_op] >> final_decision_op
