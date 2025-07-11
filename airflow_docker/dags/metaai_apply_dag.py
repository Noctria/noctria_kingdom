# dags/metaai_apply_dag.py

from datetime import datetime
from typing import Dict

from airflow.decorators import dag, task, param

# --- 王国の中枢モジュールをインポート ---
from core.path_config import LOGS_DIR
from core.logger import setup_logger
from scripts.apply_best_params_to_metaai import apply_best_params_to_metaai

# --- DAG専用の記録係をセットアップ ---
dag_log_path = LOGS_DIR / "dags" / "metaai_apply_dag.log"
logger = setup_logger("MetaAIApplyDAG", dag_log_path)

# === DAG定義 (TaskFlow APIを使用) ===
@dag(
    dag_id="metaai_apply_dag",
    schedule=None,  # 手動実行 or 他DAGからのトリガー前提
    start_date=datetime(2025, 6, 1),
    catchup=False,
    tags=["noctria", "metaai", "retrain", "apply"],
    description="📌 MetaAIに指定された最適パラメータを適用し、再学習・評価・保存する単体DAG",
    # ★改善点: 手動実行時にJSONでパラメータを受け取る
    params={
        "best_params": param(
            {},  # デフォルト値は空の辞書
            type="object",
            title="Best Hyperparameters",
            description="適用する最適化済みハイパーパラメータをJSON形式で入力します。"
        )
    }
)
def metaai_apply_pipeline():
    """
    指定されたパラメータでMetaAIモデルを再学習し、
    バージョン管理されたモデルとして保存するパイプライン。
    """

    @task
    def apply_task(params: Dict) -> Dict:
        """
        DAG実行時に渡されたパラメータを使って、再学習プロセスを実行するタスク
        """
        best_params = params.get("best_params")
        if not best_params:
            logger.error("❌ 実行パラメータ 'best_params' が指定されていません。")
            raise ValueError("Configuration 'best_params' is required to run this DAG.")

        logger.info(f"🧠 MetaAIへの叡智継承を開始します (パラメータ: {best_params})")
        
        # 外部スクリプトを呼び出し、結果（モデル情報）を受け取る
        model_info = apply_best_params_to_metaai(best_params=best_params)
        
        logger.info(f"✅ MetaAIへの継承が完了しました: {model_info}")
        return model_info

    # --- パイプラインの実行 ---
    apply_task(params="{{ params }}")

# DAGのインスタンス化
metaai_apply_pipeline()
