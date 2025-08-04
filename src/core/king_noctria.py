#!/usr/bin/env python3
# coding: utf-8

"""
👑 King Noctria (理想型 v3.0)
- decision_id, caller, reason で統治判断を一元管理
- 全DAG/AI/臣下呼び出し・御前会議・トリガーでdecision_idを必ず発行・伝搬
- 統治履歴は全てdecision_id単位でJSONログ保存
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import pandas as pd
import numpy as np

import requests

from src.veritas.veritas_machina import VeritasMachina
from src.strategies.prometheus_oracle import PrometheusOracle
from src.strategies.aurus_singularis import AurusSingularis
from src.strategies.levia_tempest import LeviaTempest
from src.strategies.noctus_sentinella import NoctusSentinella
from src.strategies.hermes_cognitor import HermesCognitorStrategy

from core.path_config import AIRFLOW_API_BASE

KING_LOG_PATH = "/opt/airflow/data/king_decision_log.json"  # 統治決定ログパス（パスは適宜調整）

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - 👑 KingNoctria: %(message)s')

class KingNoctria:
    def __init__(self):
        logging.info("王の評議会を構成するため、五臣を招集します。")
        self.veritas = VeritasMachina()
        self.prometheus = PrometheusOracle()
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.hermes = HermesCognitorStrategy()
        logging.info("五臣の招集が完了しました。")

    def _generate_decision_id(self, prefix="KC"):
        dt = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique = uuid.uuid4().hex[:6].upper()
        return f"{prefix}-{dt}-{unique}"

    def _save_king_log(self, entry: dict):
        try:
            with open(KING_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logging.error(f"King log保存失敗: {e}")

    def hold_council(self, market_data: dict, caller="king_routes", reason="御前会議決裁") -> dict:
        decision_id = self._generate_decision_id()
        timestamp = datetime.now().isoformat()
        logging.info(f"--------------------\n📣 御前会議を開催（decision_id={decision_id}）…")

        # 臣下AIの報告収集
        aurus_proposal = self.aurus.propose(market_data)
        levia_proposal = self.levia.propose(market_data)
        prometheus_forecast = self.prometheus.predict(n_days=7)
        hermes_explanation = self.hermes.propose({
            "features": market_data,
            "labels": [
                "Aurus: " + aurus_proposal.get('signal', ''),
                "Levia: " + levia_proposal.get('signal', '')
            ],
            "reason": reason
        })

        # 決定プロセス
        primary_action = aurus_proposal.get('signal')
        if primary_action == "HOLD":
            logging.info("Aurusは静観を推奨。Leviaの短期的な見解を求めます。")
            primary_action = levia_proposal.get('signal')
        logging.info(f"主たる進言は『{primary_action}』と決定しました。")

        noctus_assessment = self.noctus.assess(market_data, primary_action)
        final_decision = primary_action
        if noctus_assessment.get('decision') == 'VETO':
            logging.warning(f"Noctusが拒否権を発動！理由: {noctus_assessment.get('reason')}")
            logging.warning("安全を最優先し、最終判断を『HOLD』に変更します。")
            final_decision = "HOLD"
        else:
            logging.info("Noctusは行動を承認。進言通りに最終判断を下します。")
        logging.info(f"👑 下される王命: 『{final_decision}』\n--------------------")

        council_report = {
            "decision_id": decision_id,
            "timestamp": timestamp,
            "caller": caller,
            "reason": reason,
            "final_decision": final_decision,
            "assessments": {
                "aurus_proposal": aurus_proposal,
                "levia_proposal": levia_proposal,
                "noctus_assessment": noctus_assessment,
                "prometheus_forecast": prometheus_forecast,
                "hermes_explanation": hermes_explanation
            }
        }
        self._save_king_log(council_report)
        return council_report

    def _trigger_dag(self, dag_id: str, conf: Optional[Dict[str, Any]] = None,
                     airflow_user: str = "admin", airflow_pw: str = "admin",
                     caller="king_noctria", reason="王命トリガー") -> dict:
        decision_id = self._generate_decision_id()
        payload_conf = conf or {}
        payload_conf.update({
            "decision_id": decision_id,
            "caller": caller,
            "reason": reason,
        })
        endpoint = f"{AIRFLOW_API_BASE}/api/v1/dags/{dag_id}/dagRuns"
        auth = (airflow_user, airflow_pw)
        timestamp = datetime.now().isoformat()
        try:
            resp = requests.post(endpoint, json={"conf": payload_conf}, auth=auth)
            resp.raise_for_status()
            log_entry = {
                "decision_id": decision_id,
                "timestamp": timestamp,
                "dag_id": dag_id,
                "trigger_conf": payload_conf,
                "caller": caller,
                "reason": reason,
                "trigger_type": "dag",
                "status": "success",
                "result": resp.json()
            }
            self._save_king_log(log_entry)
            return {"status": "success", "result": resp.json()}
        except Exception as e:
            log_entry = {
                "decision_id": decision_id,
                "timestamp": timestamp,
                "dag_id": dag_id,
                "trigger_conf": payload_conf,
                "caller": caller,
                "reason": reason,
                "trigger_type": "dag",
                "status": "error",
                "error": str(e)
            }
            self._save_king_log(log_entry)
            logging.error(f"Airflow DAG [{dag_id}] トリガー失敗: {e}")
            return {"status": "error", "error": str(e)}

    # 例：Replay DAG発令
    def trigger_replay(self, log_path: str, caller="king_noctria", reason="Replay再送") -> dict:
        conf = {"log_path": log_path}
        return self._trigger_dag("veritas_replay_dag", conf, caller=caller, reason=reason)

    # 他のDAGトリガー系も同じ思想で
    def trigger_generate(self, params: dict, caller="king_noctria", reason="戦略生成") -> dict:
        return self._trigger_dag("veritas_generate_dag", params, caller=caller, reason=reason)
    def trigger_eval(self, params: dict, caller="king_noctria", reason="戦略一括評価") -> dict:
        return self._trigger_dag("veritas_evaluation_pipeline", params, caller=caller, reason=reason)
    def trigger_act(self, params: dict, caller="king_noctria", reason="Act記録") -> dict:
        return self._trigger_dag("veritas_act_record_dag", params, caller=caller, reason=reason)
    def trigger_push(self, params: dict, caller="king_noctria", reason="GitHub Push") -> dict:
        return self._trigger_dag("veritas_push_dag", params, caller=caller, reason=reason)
    def trigger_recheck(self, params: dict, caller="king_noctria", reason="再評価") -> dict:
        return self._trigger_dag("veritas_recheck_dag", params, caller=caller, reason=reason)

if __name__ == "__main__":
    logging.info("--- 王の中枢機能、単独試練の儀を開始 ---")

    king = KingNoctria()

    # ダミーデータで御前会議
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

    # テスト：DAGトリガー（replay）
    test_log_path = "/opt/airflow/data/pdca_logs/veritas_orders/sample_pdca_log.json"
    replay_result = king.trigger_replay(test_log_path)
    print("[Airflow再送DAG起動] result =", replay_result)

    logging.info("--- 王の中枢機能、単独試練の儀を完了 ---")
