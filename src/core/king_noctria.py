#!/usr/bin/env python3
# coding: utf-8

"""
👑 King Noctria (v2.2 - Hermes統合版)
- 五臣（Aurus, Levia, Noctus, Prometheus, Hermes）による統治AI。
- Hermes Cognitor（LLM戦略）を追加。
"""
import logging
import json
import pandas as pd
import numpy as np

import requests
from typing import Optional, Dict, Any

from src.veritas.veritas_machina import VeritasMachina
from src.strategies.prometheus_oracle import PrometheusOracle
from src.strategies.aurus_singularis import AurusSingularis
from src.strategies.levia_tempest import LeviaTempest
from src.strategies.noctus_sentinella import NoctusSentinella
from src.strategies.hermes_cognitor import HermesCognitorStrategy  # ← 追加

from core.path_config import (
    AIRFLOW_API_BASE,
)

DAG_ID_VERITAS_REPLAY = "veritas_replay_dag"
DAG_ID_VERITAS_GENERATE = "veritas_generate_dag"
DAG_ID_VERITAS_RECHECK = "veritas_recheck_dag"
DAG_ID_VERITAS_PUSH = "veritas_push_dag"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - 👑 KingNoctria: %(message)s')

class KingNoctria:
    def __init__(self):
        logging.info("王の評議会を構成するため、五臣を招集します。")
        self.veritas = VeritasMachina()
        self.prometheus = PrometheusOracle()
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.hermes = HermesCognitorStrategy()  # ← Hermes Cognitor追加
        logging.info("五臣の招集が完了しました。")

    def hold_council(self, market_data: dict) -> dict:
        logging.info("--------------------")
        logging.info("📣 御前会議を開催します…")
        logging.info("各臣下からの報告を収集中…")

        aurus_proposal = self.aurus.propose(market_data)
        levia_proposal = self.levia.propose(market_data)
        prometheus_forecast = self.prometheus.predict(days=7)  # ← Prometheusの予測も活用
        hermes_explanation = self.hermes.propose({
            "features": market_data,
            "labels": ["Aurus: " + aurus_proposal['signal'], "Levia: " + levia_proposal['signal']],
            "reason": "定例御前会議"
        })  # ← Hermes Cognitorの説明生成

        primary_action = aurus_proposal['signal']
        if primary_action == "HOLD":
            logging.info("Aurusは静観を推奨。Leviaの短期的な見解を求めます。")
            primary_action = levia_proposal['signal']
        logging.info(f"主たる進言は『{primary_action}』と決定しました。")

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
                "prometheus_forecast": prometheus_forecast,      # ← Prometheusの予測結果を追加
                "hermes_explanation": hermes_explanation         # ← Hermesの説明を追加
            }
        }
        return council_report

    # Airflow統治命令インターフェイスは変更なし（省略）
    def _trigger_dag(self, dag_id: str, conf: Optional[Dict[str, Any]] = None,
                     airflow_user: str = "admin", airflow_pw: str = "admin") -> dict:
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

    # 他トリガーメソッドも変更なし（省略）

if __name__ == "__main__":
    logging.info("--- 王の中枢機能、単独試練の儀を開始 ---")

    king = KingNoctria()

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

    test_log_path = "/opt/airflow/data/pdca_logs/veritas_orders/sample_pdca_log.json"
    replay_result = king.trigger_replay(test_log_path)
    print("[Airflow再送DAG起動] result =", replay_result)

    logging.info("--- 王の中枢機能、単独試練の儀を完了 ---")
