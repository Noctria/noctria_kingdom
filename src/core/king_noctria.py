#!/usr/bin/env python3
# coding: utf-8

"""
👑 King Noctria (理想型 v3.2) - Noctusにリスク・ロット計算を委譲版
- decision_id, caller, reason で統治判断を一元管理
- 全DAG/AI/臣下呼び出し・御前会議・トリガーでdecision_idを必ず発行・伝搬
- 統治履歴は全てdecision_id単位でJSONログ保存
- Do層 order_execution.py をリスクガード・SL強制付きで一元制御
- ロット/リスク計算はNoctus（NoctusSentinella）へ委譲！
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

from src.execution.order_execution import OrderExecution

from core.path_config import AIRFLOW_API_BASE

KING_LOG_PATH = "/opt/airflow/data/king_decision_log.json"

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
        self.order_executor = OrderExecution(api_url="http://host.docker.internal:5001/order")
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

    # --- ★ Noctusに計算委譲！ ---
    def order_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss_price: float,
        capital: float,
        risk_percent: float = 0.01,
        feature_dict: Optional[dict] = None,
        caller: str = "king_noctria",
        reason: str = "AI指令自動注文"
    ) -> dict:
        """
        王命による安全発注メソッド。ロット計算とリスク許可判定はNoctusに委譲。
        """
        # --- 1. ロット/リスク判定をNoctusに依頼 ---
        if feature_dict is None:
            # 最低限必要な情報だけ組み立て
            feature_dict = {
                "price": entry_price,
                "volume": 100,         # 仮値。実運用ではPlan層feature_dict推奨
                "spread": 0.01,        # 仮値
                "volatility": 0.15,    # 仮値
                "historical_data": pd.DataFrame({"Close": np.random.normal(entry_price, 2, 100)})
            }
        # Noctusに"計算してもらう"（仮想メソッド。実装はNoctusに加筆）
        noctus_result = self.noctus.calculate_lot_and_risk(
            feature_dict=feature_dict,
            side=side,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            capital=capital,
            risk_percent=risk_percent,
            decision_id=self._generate_decision_id(),
            caller=caller,
            reason=reason
        )
        # VETOなら終了
        if noctus_result["decision"] != "APPROVE":
            self._save_king_log({
                "timestamp": datetime.now().isoformat(),
                "decision_id": noctus_result.get("decision_id", ""),
                "caller": caller,
                "reason": reason,
                "symbol": symbol,
                "side": side,
                "entry_price": entry_price,
                "stop_loss": stop_loss_price,
                "capital": capital,
                "risk_percent": risk_percent,
                "noctus_result": noctus_result,
                "status": "REJECTED"
            })
            return {"status": "rejected", "noctus_result": noctus_result}

        lot = noctus_result["lot"]
        # --- 2. Do層API発注（SL必須） ---
        result = self.order_executor.execute_order(
            symbol=symbol,
            lot=lot,
            order_type=side,
            entry_price=entry_price,
            stop_loss=stop_loss_price
        )
        # --- 3. 王の決裁ログ記録 ---
        order_log = {
            "timestamp": datetime.now().isoformat(),
            "decision_id": noctus_result.get("decision_id", self._generate_decision_id()),
            "caller": caller,
            "reason": reason,
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "stop_loss": stop_loss_price,
            "lot": lot,
            "capital": capital,
            "risk_percent": risk_percent,
            "noctus_result": noctus_result,
            "api_result": result,
            "status": "EXECUTED"
        }
        self._save_king_log(order_log)
        return result

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

    # ...（DAGトリガー系は従来どおり）...

if __name__ == "__main__":
    logging.info("--- 王の中枢機能、単独試練の儀を開始 ---")

    king = KingNoctria()

    # 例：AI/PDCA/DAGからの公式発注ラッパ使用例
    result = king.order_trade(
        symbol="USDJPY",
        side="buy",
        entry_price=157.20,
        stop_loss_price=156.70,
        capital=20000,           # 現口座資金
        risk_percent=0.007,      # 0.7%など
        caller="AIシナリオ",
        reason="AI推奨取引"
    )
    print("公式発注結果:", result)

    logging.info("--- 王の中枢機能、単独試練の儀を完了 ---")
