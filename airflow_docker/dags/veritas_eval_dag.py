#!/usr/bin/env python3
# coding: utf-8

"""
✅ Veritas Evaluation Pipeline DAG (v2.0)
- Veritasが生成した戦略を動的に評価し、採用/不採用を判断し、その結果を記録する。
- 動的タスクマッピング（.expand）を用いて、複数の戦略を並列で効率的に評価する。
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from airflow.decorators import dag, task

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: Airflowが'src'モジュールを見つけられるように、プロジェクトルートをシステムパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.path_config import STRATEGIES_VERITAS_GENERATED_DIR, ACT_LOG_DIR
# ✅ 修正: リファクタリング後のモジュールを正しくインポート
from src.core.strategy_evaluator import evaluate_strategy, log_evaluation_result

# === DAG基本設定 ===
default_args = {
    'owner': 'VeritasCouncil',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 1),
    'retries': 0,
}

@dag(
    dag_id='veritas_evaluation_pipeline',
    default_args=default_args,
    description='Veritas生成戦略の評価・採用判定DAG（動的タスク・並列処理最適化版）',
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
        """`veritas_generated`ディレクトリから評価対象の戦略ファイル名（ID）のリストを取得する"""
        if not STRATEGIES_VERITAS_GENERATED_DIR.exists():
            logging.warning(f"⚠️ 戦略生成ディレクトリが存在しません: {STRATEGIES_VERITAS_GENERATED_DIR}")
            return []
        
        # .pyで終わり、__で始まらないファイル名（拡張子なし）をリスト化
        new_strategies = [
            f.stem for f in STRATEGIES_VERITAS_GENERATED_DIR.iterdir()
            if f.is_file() and f.suffix == '.py' and not f.name.startswith('__')
        ]
        logging.info(f"🔍 {len(new_strategies)}件の新しい戦略を評価対象として発見しました。")
        return new_strategies

    @task
    def evaluate_one_strategy(strategy_id: str) -> Dict[str, Any]:
        """単一の戦略を評価し、結果を辞書として返す"""
        import logging
        logging.info(f"📊 評価開始: {strategy_id}")
        try:
            # ✅ 修正: リファクタリング後のevaluate_strategyを呼び出す
            result = evaluate_strategy(strategy_id)
            result["status"] = "ok"
        except Exception as e:
            logging.error(f"🚫 評価エラー: {strategy_id} ➜ {e}", exc_info=True)
            result = {"strategy": strategy_id, "status": "error", "error_message": str(e)}
            
        return result

    @task
    def log_all_results(evaluation_results: List[Dict]):
        """全ての評価結果をループして、個別のログファイルとして保存する"""
        import logging
        if not evaluation_results:
            logging.info("評価対象の戦略がなかったため、ログ記録をスキップします。")
            return

        logging.info(f"📝 {len(evaluation_results)}件の評価結果を王国の書庫に記録します…")
        for result in evaluation_results:
            if result.get("status") == "ok":
                # ✅ 修正: リファクタリング後のlog_evaluation_resultを呼び出す
                log_evaluation_result(result)
        logging.info("✅ 全ての評価記録の保存が完了しました。")

    # --- パイプラインの定義 ---
    strategy_ids = get_strategies_to_evaluate()
    
    # 動的タスクマッピング: 戦略IDのリストを元に、並列で評価タスクを生成
    evaluated_results = evaluate_one_strategy.expand(strategy_id=strategy_ids)
    
    # 全ての評価が終わってから、結果を集約してログに記録
    log_all_results(evaluation_results=evaluated_results)

# DAGのインスタンス化
veritas_evaluation_pipeline()
