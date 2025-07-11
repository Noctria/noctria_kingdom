import os
import importlib.util
from datetime import datetime, timedelta

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# ================================================
# ★ 修正: 新しいimportルールを適用
# ================================================
# `PYTHONPATH`が設定されたため、sys.pathハックは不要。
# 全てのモジュールは、srcを起点とした絶対パスでインポートする。
from core.path_config import LOGS_DIR, STRATEGIES_DIR
from core.logger import setup_logger
from noctria_ai.noctria import Noctria # `noctria_ai`モジュールからインポート

# ================================================
# 📜 王命: DAG共通設定
# ================================================
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ================================================
# 👑 王命: Noctria Kingdom 統合戦略DAG
# ================================================
with DAG(
    dag_id='noctria_kingdom_dag',
    default_args=default_args,
    description='Noctria王国戦略統合DAG（official戦略を動的適用）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'kingdom', 'veritas']
) as dag:

    # ================================================
    # 🏰 王国記録係（ログ）の召喚
    # ================================================
    dag_log_path = LOGS_DIR / "dags" / "noctria_kingdom_dag.log"
    logger = setup_logger("NoctriaKingdomDAG", dag_log_path)

    OFFICIAL_DIR = STRATEGIES_DIR / "official"

    def create_strategy_task(strategy_name, strategy_path):
        """動的に戦略実行タスクを生成する関数"""
        def strategy_callable(**kwargs):
            try:
                spec = importlib.util.spec_from_file_location(strategy_name, strategy_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if not hasattr(module, "simulate"):
                    logger.warning(f"❌ {strategy_name} は simulate() を定義していません")
                    return

                result = module.simulate()
                logger.info(f"[{strategy_name}] result: {result}")
                kwargs["ti"].xcom_push(key=f"{strategy_name}_decision", value=result)

            except Exception as e:
                logger.error(f"[{strategy_name}] 実行エラー: {e}", exc_info=True)
                raise

        return strategy_callable

    # ================================================
    # ⚔️ 各戦略の並行実行
    # ================================================
    strategy_tasks = []
    # officialディレクトリが存在し、アクセス可能か確認
    if OFFICIAL_DIR.exists() and os.access(OFFICIAL_DIR, os.R_OK):
        for fname in os.listdir(OFFICIAL_DIR):
            if fname.endswith(".py") and not fname.startswith("__"):
                strategy_name = os.path.splitext(fname)[0]
                strategy_path = str(OFFICIAL_DIR / fname)
                task = PythonOperator(
                    task_id=f"{strategy_name}_strategy",
                    python_callable=create_strategy_task(strategy_name, strategy_path)
                )
                strategy_tasks.append((strategy_name, task))

    # ================================================
    # 👑 MetaAIによる最終判断
    # ================================================
    def noctria_final_decision(**kwargs):
        ti = kwargs['ti']
        decisions = {}
        for strategy_name, _ in strategy_tasks:
            val = ti.xcom_pull(key=f"{strategy_name}_decision", task_ids=f"{strategy_name}_strategy")
            decisions[strategy_name] = val
        
        logger.info(f"👑 Noctriaが受け取った判断: {decisions}")
        
        # ★ Noctria（オーケストレーター）をインスタンス化
        # この中で学習済みのRLエージェントなどがロードされる
        noctria_orchestrator = Noctria()
        
        # ★ 市場データと戦略の意見から最終判断を下す
        # (この部分はNoctriaクラスの実装に応じて要調整)
        final_action = noctria_orchestrator.decide_final_action(decisions)
        
        logger.info(f"🏰 王国最終判断: {final_action}")

    final_task = PythonOperator(
        task_id="noctria_final_decision",
        python_callable=noctria_final_decision
    )

    # ================================================
    # 🔗 依存関係の定義
    # ================================================
    if strategy_tasks:
        for _, task in strategy_tasks:
            task >> final_task
