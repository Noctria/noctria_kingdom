import os
import importlib.util
from datetime import datetime, timedelta

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# 💡 DAG定義以外で実行されるトップレベル処理は避ける（importやpathのみOK）
from core.path_config import LOGS_DIR, STRATEGIES_DIR

# ========================================
# 👑 DAG共通設定
# ========================================
default_args = {
    'owner': 'Noctria',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ========================================
# 🏰 Noctria Kingdom 統合DAG
# ========================================
with DAG(
    dag_id='noctria_kingdom_dag',
    default_args=default_args,
    description='Noctria王国統合DAG（official戦略を動的に実行）',
    schedule_interval=None,
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=['noctria', 'kingdom', 'veritas']
) as dag:

    def create_strategy_task(strategy_name, strategy_path):
        """戦略ごとのPythonタスク関数を生成"""
        def strategy_callable(**kwargs):
            import logging
            logger = logging.getLogger(f"{strategy_name}")

            try:
                spec = importlib.util.spec_from_file_location(strategy_name, strategy_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if not hasattr(module, "simulate"):
                    logger.warning(f"❌ {strategy_name} は simulate() を定義していません")
                    return None

                result = module.simulate()
                logger.info(f"[{strategy_name}] result: {result}")
                kwargs["ti"].xcom_push(key=f"{strategy_name}_decision", value=result)
                return result

            except Exception as e:
                logger.error(f"[{strategy_name}] 実行エラー: {e}", exc_info=True)
                raise

        return strategy_callable

    # 📁 戦略ディレクトリの走査とタスク作成
    strategy_tasks = []
    OFFICIAL_DIR = STRATEGIES_DIR / "official"
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

    # 🧠 Noctria による統合判断
    def noctria_final_decision(**kwargs):
        import logging
        logger = logging.getLogger("NoctriaFinalDecision")

        ti = kwargs['ti']
        decisions = {}

        for strategy_name, _ in strategy_tasks:
            val = ti.xcom_pull(key=f"{strategy_name}_decision", task_ids=f"{strategy_name}_strategy")
            decisions[strategy_name] = val

        logger.info(f"👑 Noctriaが受け取った判断: {decisions}")

        # 💡 重いインポートを関数内に移動（遅延ロード）
        from core.logger import setup_logger
        from noctria_ai.noctria import Noctria

        # ロガーセットアップ（必要ならファイル出力に変更）
        log_path = LOGS_DIR / "dags" / "noctria_kingdom_dag.log"
        setup_logger("NoctriaKingdomDAG", log_path)

        # Noctria AI オーケストレータの判断
        orchestrator = Noctria()
        final_action = orchestrator.decide_final_action(decisions)

        logger.info(f"🏰 王国最終判断: {final_action}")
        return final_action

    final_task = PythonOperator(
        task_id="noctria_final_decision",
        python_callable=noctria_final_decision
    )

    # 🔗 依存関係の定義
    if strategy_tasks:
        for _, task in strategy_tasks:
            task >> final_task
