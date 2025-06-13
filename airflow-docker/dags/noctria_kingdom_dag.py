import sys
sys.path.append('/opt/airflow')  # Airflowパス追加

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

from core.noctria import Noctria
from strategies.Aurus_Singularis import AurusSingularis
from strategies.Levia_Tempest import LeviaTempest
from strategies.Noctus_Sentinella import NoctusSentinella
from strategies.Prometheus_Oracle import PrometheusOracle

# ✅ DAG共通設定
default_args = {
    'owner': 'NoctriaKingdom',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='noctria_kingdom_dag',
    default_args=default_args,
    description='🏰 Noctria Kingdom 全AIを統括する戦略連携DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'kingdom', 'coordinated'],
)

# --- 各戦略AIのタスク定義（臣下） ---
def run_aurus():
    aurus = AurusSingularis()
    decision = aurus.process({
        "price": 1.234, "trend_strength": 0.7, "volume": 200,
        "order_block": 0.4, "volatility": 0.15
    })
    print(f"📈 Aurusの判断: {decision}")

def run_levia():
    levia = LeviaTempest()
    decision = levia.process({
        "price": 1.205, "previous_price": 1.203, "volume": 300,
        "spread": 0.01, "order_block": 0.2, "volatility": 0.1
    })
    print(f"⚡ Leviaの判断: {decision}")

def run_noctus():
    noctus = NoctusSentinella()
    decision = noctus.process({
        "price": 1.222, "volume": 150, "spread": 0.02,
        "order_block": 0.3, "volatility": 0.2,
        "price_history": [1.21, 1.22, 1.23]
    })
    print(f"🛡️ Noctusの判断: {decision}")

def run_prometheus():
    prometheus = PrometheusOracle()
    decision = prometheus.process({
        "cpi": 3.1, "gdp_growth": 2.2, "interest_rate": 1.5,
        "sentiment": 0.6, "geopolitical_risk": 0.3
    })
    print(f"🔮 Prometheusの判断: {decision}")

# --- 王の統合判断 ---
def run_noctria_king():
    king = Noctria()
    result = king.execute_trade()
    print(f"👑 王Noctriaの最終判断: {result}")


# ✅ DAG構築
with dag:
    aurus_task = PythonOperator(task_id="aurus_task", python_callable=run_aurus)
    levia_task = PythonOperator(task_id="levia_task", python_callable=run_levia)
    noctus_task = PythonOperator(task_id="noctus_task", python_callable=run_noctus)
    prometheus_task = PythonOperator(task_id="prometheus_task", python_callable=run_prometheus)

    noctria_task = PythonOperator(task_id="noctria_final_decision", python_callable=run_noctria_king)

    # 🏰 王国の臣下タスクを先に実行 → 王の判断
    [aurus_task, levia_task, noctus_task, prometheus_task] >> noctria_task
