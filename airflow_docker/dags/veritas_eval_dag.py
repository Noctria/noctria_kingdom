# dags/veritas_eval_dag.py

import os
import json
from datetime import datetime, timedelta

from airflow.decorators import dag, task

# --- 王国の中枢モジュールをインポート ---
from core.path_config import STRATEGIES_DIR, LOGS_DIR, MARKET_DATA_CSV
from core.logger import setup_logger
from core.strategy_evaluator import evaluate_strategy, is_strategy_adopted
from core.market_loader import load_market_data

# --- 登用試験の記録係をセットアップ ---
dag_log_path = LOGS_DIR / "dags" / "veritas_eval_dag.log"
logger = setup_logger("VeritasEvalDAG", dag_log_path)

# === DAG基本設定 ===
default_args = {
    'owner': 'Veritas',
    'depends_on_past': False,
    'start_date': datetime(2025, 6, 1),
    'retries': 0,
}

@dag(
    dag_id='veritas_eval_dag',
    default_args=default_args,
    description='✅ Veritas生成戦略の評価・採用判定DAG（動的タスク対応）',
    schedule_interval=None,
    catchup=False,
    tags=['veritas', 'evaluation', 'pdca'],
)
def veritas_evaluation_pipeline():
    """
    Veritasが生成した戦略を動的に評価し、採用するパイプライン
    """

    @task
    def get_strategies_to_evaluate() -> list[str]:
        """
        `veritas_generated`ディレクトリから、まだ評価されていない新しい戦略ファイルのリストを取得する
        """
        generated_dir = STRATEGIES_DIR / "veritas_generated"
        # (将来的な改善: 既に評価済みの戦略はスキップするロジックを追加)
        
        if not generated_dir.exists():
            logger.warning(f"⚠️ 戦略生成ディレクトリが存在しません: {generated_dir}")
            return []
            
        new_strategies = [
            str(generated_dir / fname)
            for fname in os.listdir(generated_dir)
            if fname.endswith(".py") and not fname.startswith("__")
        ]
        logger.info(f"🔍 {len(new_strategies)}件の新しい戦略を評価対象として発見しました。")
        return new_strategies

    @task
    def evaluate_one_strategy(strategy_path: str) -> dict:
        """
        単一の戦略ファイルを評価し、結果を辞書として返す
        """
        filename = os.path.basename(strategy_path)
        logger.info(f"📊 評価開始: {filename}")
        
        try:
            # 実際の市場データは一度だけロードして渡すのが効率的だが、
            # タスク分離のため、ここでは各タスクでロードする
            market_data = load_market_data(str(MARKET_DATA_CSV))
            result = evaluate_strategy(strategy_path, market_data)
            result["status"] = "ok"
        except Exception as e:
            logger.error(f"🚫 評価エラー: {filename} ➜ {e}", exc_info=True)
            result = {"status": "error", "error_message": str(e)}
            
        result["timestamp"] = datetime.utcnow().isoformat()
        result["filename"] = filename
        result["original_path"] = strategy_path
        
        return result

    @task
    def decide_and_promote_strategy(eval_result: dict):
        """
        評価結果に基づき、戦略の採用を決定し、ファイルを移動する
        """
        filename = eval_result.get("filename")
        if eval_result.get("status") != "ok":
            logger.warning(f"⚠️ 評価がエラーのため、{filename}の採用判断をスキップします。")
            return

        if is_strategy_adopted(eval_result):
            official_dir = STRATEGIES_DIR / "official"
            official_dir.mkdir(parents=True, exist_ok=True)
            
            source_path = Path(eval_result["original_path"])
            destination_path = official_dir / filename
            
            try:
                # ★改善点: ファイルを移動し、生成元からは削除する
                source_path.rename(destination_path)
                logger.info(f"✅ 採用・昇格: {filename} -> {destination_path}")
                eval_result["status"] = "adopted"
                # (将来的な改善: ここでveritas_push_dagをトリガーするのが理想)
            except Exception as e:
                logger.error(f"❌ ファイル移動エラー: {filename}, エラー: {e}", exc_info=True)
                eval_result["status"] = "promotion_failed"
        else:
            logger.info(f"❌ 不採用: {filename}")
            eval_result["status"] = "rejected"
            # (将来的な改善: 不採用の戦略ファイルをアーカイブディレクトリに移動する)

        # 最終結果をログに記録
        log_path = LOGS_DIR / "veritas_eval_result.json"
        # (注意: このログは追記専用。読み書きすると競合するため、各タスクが個別に出力するのが望ましい)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(eval_result) + "\n")

    # --- パイプラインの定義 ---
    strategy_list = get_strategies_to_evaluate()
    
    # 動的タスクマッピング: strategy_listの各要素に対して、後続のタスクを生成
    evaluated_results = evaluate_one_strategy.expand(strategy_path=strategy_list)
    decide_and_promote_strategy.expand(eval_result=evaluated_results)

# DAGのインスタンス化
veritas_evaluation_pipeline()
