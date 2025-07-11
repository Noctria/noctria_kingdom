# dags/veritas_eval_dag.py

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

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
    description='✅ Veritas生成戦略の評価・採用判定DAG（動的タスク・並列処理最適化版）',
    schedule_interval=None,
    catchup=False,
    tags=['veritas', 'evaluation', 'pdca'],
)
def veritas_evaluation_pipeline():
    """
    Veritasが生成した戦略を動的に評価し、採用するパイプライン
    """

    @task
    def get_strategies_to_evaluate() -> List[str]:
        """`veritas_generated`ディレクトリから評価対象の戦略ファイルリストを取得する"""
        generated_dir = STRATEGIES_DIR / "veritas_generated"
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
    def load_evaluation_data() -> str:
        """
        ★改善点: 評価用の市場データを一度だけロードし、内容をJSON文字列で返す
        (Pandas DataFrameはXComsのサイズ制限を超える可能性があるため、JSON化が安全)
        """
        logger.info(f"💾 市場データをロード中: {MARKET_DATA_CSV}")
        market_data = load_market_data(str(MARKET_DATA_CSV))
        return market_data.to_json(orient='split')

    @task
    def evaluate_one_strategy(strategy_path: str, market_data_json: str) -> Dict:
        """単一の戦略ファイルを評価し、結果を辞書として返す"""
        filename = os.path.basename(strategy_path)
        logger.info(f"📊 評価開始: {filename}")
        
        market_data = pd.read_json(market_data_json, orient='split')
        
        try:
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
    def decide_and_promote_strategy(eval_result: Dict) -> Dict:
        """評価結果に基づき、戦略の採用を決定し、ファイルを移動する。最終的な結果を返す。"""
        filename = eval_result.get("filename")
        if eval_result.get("status") != "ok":
            logger.warning(f"⚠️ 評価がエラーのため、{filename}の採用判断をスキップします。")
            return eval_result

        if is_strategy_adopted(eval_result):
            official_dir = STRATEGIES_DIR / "official"
            official_dir.mkdir(parents=True, exist_ok=True)
            
            source_path = Path(eval_result["original_path"])
            destination_path = official_dir / filename
            
            try:
                source_path.rename(destination_path)
                logger.info(f"✅ 採用・昇格: {filename} -> {destination_path}")
                eval_result["status"] = "adopted"
            except Exception as e:
                logger.error(f"❌ ファイル移動エラー: {filename}, エラー: {e}", exc_info=True)
                eval_result["status"] = "promotion_failed"
        else:
            logger.info(f"❌ 不採用: {filename}")
            eval_result["status"] = "rejected"
        
        return eval_result

    @task
    def aggregate_and_log_results(all_results: List[Dict]):
        """★改善点: 全てのタスク結果を集約し、一度に安全にログファイルへ書き込む"""
        log_path = LOGS_DIR / "veritas_eval_result.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📝 {len(all_results)}件の評価結果を最終ログに記録します: {log_path}")
        
        # 既存のログを読み込み、新しい結果をマージすることも可能だが、ここでは上書きする
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        logger.info("✅ 最終ログの記録が完了しました。")


    # --- パイプラインの定義 ---
    strategy_list = get_strategies_to_evaluate()
    market_data = load_evaluation_data()
    
    evaluated_results = evaluate_one_strategy.expand(
        strategy_path=strategy_list,
        market_data_json=market_data # market_dataの結果が各タスクにブロードキャストされる
    )
    
    promoted_results = decide_and_promote_strategy.expand(eval_result=evaluated_results)
    
    # 全ての採用判断が終わってから、結果を集約してログに記録
    aggregate_and_log_results(all_results=promoted_results)


# DAGのインスタンス化
veritas_evaluation_pipeline()
