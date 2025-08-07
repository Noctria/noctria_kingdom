import logging
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

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

    # =============================
    # ここからリファクタ後の新API
    # =============================
    def order_trade(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        direction: str,  # 'buy' or 'sell'
        account_info: dict,
        caller="king_noctria",
        reason="AI発注"
    ) -> dict:
        """
        王命による取引発注。リスク判定・ロット計算はNoctusに委譲。発注はOrderExecutionに命じる。
        """
        decision_id = self._generate_decision_id()
        timestamp = datetime.now().isoformat()

        # Step1: Noctusにリスク評価・ロット計算を命じる
        risk_result = self.noctus.calculate_lot_and_risk(
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            direction=direction,
            account_info=account_info,
            risk_percent_min=0.5,
            risk_percent_max=1.0
        )

        if not risk_result.get("ok"):
            entry = {
                "decision_id": decision_id,
                "timestamp": timestamp,
                "action": "order_trade",
                "symbol": symbol,
                "direction": direction,
                "status": "rejected",
                "risk_reason": risk_result.get("reason"),
                "caller": caller,
                "reason": reason,
            }
            self._save_king_log(entry)
            return entry

        lot = risk_result["lot"]
        risk_value = risk_result["risk_value"]

        # Step2: Do層（OrderExecution）へ命令
        order_result = self.order_executor.execute_order(
            symbol=symbol,
            lot=lot,
            order_type=direction,
            stop_loss=stop_loss  # 新I/F想定：必ずSLを渡す
        )

        entry = {
            "decision_id": decision_id,
            "timestamp": timestamp,
            "action": "order_trade",
            "symbol": symbol,
            "direction": direction,
            "status": "executed" if order_result.get("status") == "success" else "error",
            "lot": lot,
            "risk_value": risk_value,
            "risk_detail": risk_result,
            "order_result": order_result,
            "caller": caller,
            "reason": reason,
        }
        self._save_king_log(entry)
        return entry

    # --- 旧安全ラッパも互換用途で残してもよい（推奨はorder_tradeに移行）

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

    # ...DAGトリガー系は従来通り...

if __name__ == "__main__":
    logging.info("--- 王の中枢機能、単独試練の儀を開始 ---")

    king = KingNoctria()

    # サンプル発注コール
    dummy_account_info = {
        "capital": 20000,
        "currency": "JPY",
        # ...他の証拠金・レバレッジ情報など...
    }
    result = king.order_trade(
        symbol="USDJPY",
        entry_price=157.20,
        stop_loss=156.70,
        direction="buy",
        account_info=dummy_account_info,
        caller="AIシナリオ",
        reason="AI推奨取引"
    )
    print("公式発注結果:", result)

    logging.info("--- 王の中枢機能、単独試練の儀を完了 ---")
