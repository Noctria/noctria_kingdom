#!/usr/bin/env python3
# coding: utf-8

"""
📊 Dashboard Service
- 中央統治ダッシュボード向けに複数AI/データソースから
  データを集約し、整形して提供するサービス層
"""

import logging
from typing import Dict, Any, List

# ここに必要なモジュールをインポート
from src.core.king_noctria import KingNoctria
from src.strategies.prometheus_oracle import PrometheusOracle
from src.core.path_config import PDCA_LOG_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


def get_dashboard_data() -> Dict[str, Any]:
    """
    ダッシュボード表示用の統計と予測データを取得する。
    """
    logging.info("Dashboardデータ集約処理を開始します。")

    try:
        # 1. KingNoctriaや各臣下AIの最新統計を取得
        king = KingNoctria()
        # 仮にKingNoctriaにstats()メソッドがある想定（要実装）
        stats = {
            "avg_win_rate": 57.8,       # ダミー値
            "promoted_count": 9,
            "pushed_count": 20,
            "oracle_metrics": {"RMSE": 0.0298}
        }

        # 2. Prometheus Oracleの未来予測取得
        oracle = PrometheusOracle()
        forecast_df = oracle.predict_with_confidence(n_days=14)
        forecast = forecast_df.to_dict(orient="records") if not forecast_df.empty else []

        # 3. PDCAログの簡易集計なども追加可能
        # 例: pdca_summary = load_and_aggregate_pdca_logs(PDCA_LOG_DIR, limit=10)

        logging.info("Dashboardデータの集約が完了しました。")
        return {"stats": stats, "forecast": forecast}

    except Exception as e:
        logging.error(f"Dashboardデータの集約中にエラー: {e}")
        return {"stats": {}, "forecast": []}
