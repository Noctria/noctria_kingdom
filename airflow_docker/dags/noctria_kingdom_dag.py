import sys
import os
import glob
import importlib.util
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# sys.path を明示的に追加（Airflow上の /opt/airflow 想定）
sys.path.append('/opt/airflow')

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
    description='Noctria王国全体戦略統合DAG（XCom連携＋Veritas連動）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'kingdom'],
)

logger = setup_logger("NoctriaDecision", "/noctria_kingdom/airflow_docker/logs/noctria_decision.log")

# === 各臣下AIタスク ===
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

# === Veritas 戦略（official/以下） ===
OFFICIAL_STRATEGY_DIR = "/noctria_kingdom/strategies/official"

def load_official_strategies():
    strategies = []
    for file_path in glob.glob(os.path.join(OFFICIAL_STRATEGY_DIR, "*.py")):
        module_name = os.path.basename(file_path).replace(".py", "")
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            if hasattr(mod, "simulate"):
                strategies.append((module_name, mod.simulate))
        except Exception as e:
            logger.error(f"[Veritas] 読み込み失敗: {module_name}: {e}")
    return strategies

def dynamic_veritas_task(simulate_func, name):
    def task(**kwargs):
        logger.info(f"[Veritas_{name}] 実行開始")
        try:
            result = simulate_func()
            logger.info(f"[Veritas_{name}] 結果: {result}")
            kwargs["ti"].xcom_push(key=f"veritas_{name}_decision", value=result)
        except Exception as e:
            logger.error(f"[Veritas_{name}] 実行エラー: {e}")
    return task

# === 王による最終決定 ===
def noctria_final_decision(**kwargs):
    ti = kwargs['ti']
    decisions = {
        "Aurus": ti.xcom_pull(key='aurus_decision', task_ids='aurus_strategy'),
        "Levia": ti.xcom_pull(key='levia_decision', task_ids='levia_strategy'),
        "Noctus": ti.xcom_pull(key='noctus_decision', task_ids='noctus_strategy'),
        "Prometheus": ti.xcom_pull(key='prometheus_decision', task_ids='prometheus_strategy'),
    }

    # Veritas追加戦略も取り込み
    for mod_name, _ in load_official_strategies():
        key = f"veritas_{mod_name}_decision"
        task_id = f"veritas_strategy_{mod_name}"
        val = ti.xcom_pull(key=key, task_ids=task_id)
        decisions[f"Veritas_{mod_name}"] = val

    logger.info(f"👑 王Noctriaが受け取った判断: {decisions}")
    noctria = Noctria()
    final_action = noctria.meta_ai.decide_final_action(decisions)
    logger.info(f"🏰 王国全体の最終戦略決定: {final_action}")

# === DAG 登録 ===
with dag:
    t1 = PythonOperator(task_id='aurus_strategy', python_callable=aurus_task)
    t2 = PythonOperator(task_id='levia_strategy', python_callable=levia_task)
    t3 = PythonOperator(task_id='noctus_strategy', python_callable=noctus_task)
    t4 = PythonOperator(task_id='prometheus_strategy', python_callable=prometheus_task)

    veritas_tasks = []
    for mod_name, simulate_fn in load_official_strategies():
        task_id = f"veritas_strategy_{mod_name}"
        op = PythonOperator(
            task_id=task_id,
            python_callable=dynamic_veritas_task(simulate_fn, mod_name),
        )
        veritas_tasks.append(op)

    t5 = PythonOperator(task_id='noctria_final_decision', python_callable=noctria_final_decision)

    [t1, t2, t3, t4, *veritas_tasks] >> t5
