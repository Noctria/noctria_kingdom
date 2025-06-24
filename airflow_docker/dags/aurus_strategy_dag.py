import sys
sys.path.append('/opt/airflow')

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from strategies.aurus_singularis import AurusSingularis

default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='aurus_strategy_dag',
    default_args=default_args,
    description='⚔️ Noctria Kingdomの戦術官Aurusによるトレンド解析DAG',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'trend-analysis'],
)

def aurus_strategy_task(**kwargs):
    print("👑 王Noctria: 『Aurusよ、時の波を読み、我らが未来を照らすのだ。』")

    aurus = AurusSingularis()

    # Veritas等から渡される入力に対応（なければmock）
    market_data = kwargs.get("market_data") or {
        "price": 1.2345,
        "volume": 500,
        "sentiment": 0.7,
        "trend_strength": 0.5,
        "volatility": 0.12,
        "order_block": 0.3,
        "institutional_flow": 0.6,
        "short_interest": 0.4,
        "momentum": 0.8,
        "trend_prediction": 0.65,
        "liquidity_ratio": 1.1
    }

    decision = aurus.process(market_data)
    aurus.logger.info(f"⚔️ Aurusの戦略判断（XCom返却）: {decision}")
    print(f"🔮 Aurus: 『王よ、我が洞察によれば…選ぶべき道は【{decision}】にございます。』")
    return decision  # ✅ XCom返却

with dag:
    aurus_task = PythonOperator(
        task_id='aurus_trend_analysis_task',
        python_callable=aurus_strategy_task,
        provide_context=True,  # ✅ XCom/kwargs対応
    )
