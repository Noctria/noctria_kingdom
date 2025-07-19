#!/usr/bin/env python3
# coding: utf-8

"""
👑 King Noctria (v2.1 - Airflow統治連携版)
- Noctria王国の中枢。統治AIの全ての意思決定を司る。
- 5人の臣下AIからの進言と報告を統合し、最終的な王命を下す。
- AirflowのDAG群（再送・再評価・戦略生成・Push等）への疎結合インターフェイスを実装。
"""
import logging
import json
import pandas as pd
import numpy as np

import requests
from typing import Optional, Dict, Any

from src.veritas.veritas_machina import VeritasStrategist
from src.strategies.prometheus_oracle import PrometheusOracle
from src.strategies.aurus_singularis import AurusSingularis
from src.strategies.levia_tempest import LeviaTempest
from src.strategies.noctus_sentinella import NoctusSentinella

# パス管理とDAG名/エンドポイント管理
from core.path_config import (
    AIRFLOW_API_BASE,   # "http://localhost:8080" など
)

# DAG名定義（必要ならpath_config.py側で集約してもOK）
DAG_ID_VERITAS_REPLAY = "veritas_replay_dag"
DAG_ID_VERITAS_GENERATE = "veritas_generate_dag"
DAG_ID_VERITAS_RECHECK = "veritas_recheck_dag"
DAG_ID_VERITAS_PUSH = "veritas_push_dag"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - 👑 KingNoctria: %(message)s')

class KingNoctria:
    """
    五臣会議を主宰し、王国の最終判断を下す統治AI。
    Airflow等の下位DAG群への疎結合命令インターフェイスも兼ねる。
    """

    def __init__(self):
        logging.info("王の評議会を構成するため、五臣を招集します。")
        self.veritas = VeritasStrategist()          # 戦略立案官
        self.prometheus = PrometheusOracle()        # 未来予測官
        self.aurus = AurusSingularis()              # 総合市場分析官
        self.levia = LeviaTempest()                 # 高速スキャルピングAI
        self.noctus = NoctusSentinella()            # リスク管理官
        logging.info("五臣の招集が完了しました。")

    # -------------------------------------------
    # 1. AI会議アルゴリズム（現状維持）
    # -------------------------------------------
    def hold_council(self, market_data: dict) -> dict:
        logging.info("--------------------")
        logging.info("📣 御前会議を開催します…")
        logging.info("各臣下からの報告を収集中…")
        aurus_proposal = self.aurus.propose(market_data)
        levia_proposal = self.levia.propose(market_data)
        # Prometheus/Veritasの進言は将来拡張で利用

        # Aurus優先、静観ならLeviaを採用
        primary_action = aurus_proposal['signal']
        if primary_action == "HOLD":
            logging.info("Aurusは静観を推奨。Leviaの短期的な見解を求めます。")
            primary_action = levia_proposal['signal']
        logging.info(f"主たる進言は『{primary_action}』と決定しました。")

        # Noctusリスク評価
        noctus_assessment = self.noctus.assess(market_data, primary_action)
        final_decision = primary_action
        if noctus_assessment['decision'] == 'VETO':
            logging.warning(f"Noctusが拒否権を発動！理由: {noctus_assessment['reason']}")
            logging.warning("安全を最優先し、最終判断を『HOLD』に変更します。")
            final_decision = "HOLD"
        else:
            logging.info("Noctusは行動を承認。進言通りに最終判断を下します。")
        logging.info(f"👑 下される王命: 『{final_decision}』")
        logging.info("--------------------")

        council_report = {
            "final_decision": final_decision,
            "assessments": {
                "aurus_proposal": aurus_proposal,
                "levia_proposal": levia_proposal,
                "noctus_assessment": noctus_assessment,
                # "prometheus_forecast": prometheus_forecast,
                # "veritas_proposal": veritas_proposal,
            }
        }
        return council_report

    # -------------------------------------------
    # 2. Airflow統治命令インターフェイス
    # -------------------------------------------

    def _trigger_dag(self, dag_id: str, conf: Optional[Dict[str, Any]] = None,
                     airflow_user: str = "admin", airflow_pw: str = "admin") -> dict:
        """
        Airflow DAGをREST API経由でトリガーするユーティリティ
        """
        endpoint = f"{AIRFLOW_API_BASE}/api/v1/dags/{dag_id}/dagRuns"
        payload = {"conf": conf or {}}
        auth = (airflow_user, airflow_pw)
        try:
            resp = requests.post(endpoint, json=payload, auth=auth)
            resp.raise_for_status()
            return {"status": "success", "result": resp.json()}
        except Exception as e:
            logging.error(f"Airflow DAG [{dag_id}] トリガー失敗: {e}")
            return {"status": "error", "error": str(e)}

    def trigger_replay(self, log_path: str) -> dict:
        """
        再送DAG（veritas_replay_dag）をAirflow経由で起動
        """
        return self._trigger_dag(DAG_ID_VERITAS_REPLAY, conf={"log_path": log_path})

    def trigger_generate(self, params: Optional[Dict[str, Any]] = None) -> dict:
        """
        戦略生成DAG（veritas_generate_dag）をAirflow経由で起動
        """
        return self._trigger_dag(DAG_ID_VERITAS_GENERATE, conf=params or {})

    def trigger_recheck(self, strategy_id: str) -> dict:
        """
        戦略再評価DAG（veritas_recheck_dag）をAirflow経由で起動
        """
        return self._trigger_dag(DAG_ID_VERITAS_RECHECK, conf={"strategy_id": strategy_id})

    def trigger_push(self, strategy_id: str) -> dict:
        """
        戦略PushDAG（veritas_push_dag）をAirflow経由で起動
        """
        return self._trigger_dag(DAG_ID_VERITAS_PUSH, conf={"strategy_id": strategy_id})

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- 王の中枢機能、単独試練の儀を開始 ---")

    king = KingNoctria()
    # AI会議テスト（従来通り）
    dummy_hist_data = pd.DataFrame({
        'Close': np.random.normal(loc=150, scale=2, size=100)
    })
    dummy_hist_data['returns'] = dummy_hist_data['Close'].pct_change().dropna()
    mock_market = {
        "price": 1.2530, "previous_price": 1.2510, "volume": 160, "volatility": 0.18,
        "sma_5_vs_20_diff": 0.001, "macd_signal_diff": 0.0005, "trend_strength": 0.6, "trend_prediction": "bullish",
        "rsi_14": 60.0, "stoch_k": 70.0, "momentum": 0.8,
        "bollinger_upper_dist": -0.001, "bollinger_lower_dist": 0.009,
        "sentiment": 0.7, "order_block": 0.4, "liquidity_ratio": 1.1, "symbol": "USDJPY",
        "interest_rate_diff": 0.05, "cpi_change_rate": 0.03, "news_sentiment_score": 0.75,
        "spread": 0.012, "historical_data": dummy_hist_data
    }
    result = king.hold_council(mock_market)
    print("\n" + "="*50)
    print("📜 御前会議 最終報告書")
    print("="*50)
    print(json.dumps(result, indent=4, ensure_ascii=False))
    print("="*50)

    # Airflow再送DAGのトリガーテスト
    print("=== Airflow再送DAGトリガーテスト ===")
    test_log_path = "/opt/airflow/data/pdca_logs/veritas_orders/sample_pdca_log.json"  # 必要に応じて実パス指定
    replay_result = king.trigger_replay(test_log_path)
    print("[Airflow再送DAG起動] result =", replay_result)

    logging.info("--- 王の中枢機能、単独試練の儀を完了 ---")
