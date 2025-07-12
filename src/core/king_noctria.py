from veritas.veritas_ai import VeritasStrategist
from strategies.prometheus_oracle import PrometheusOracle
from strategies.aurus_singularis import AurusSingularis
from strategies.levia_tempest import LeviaTempest
from strategies.noctus_sentinella import NoctusSentinella

import requests

class KingNoctria:
    """
    👑 Noctria王 - 統治AIの中枢
    - 5人の臣下AIからの提案・知見をもとに最終判断を下す
    """

    def __init__(self):
        self.veritas = VeritasStrategist()
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()

    def get_prometheus_forecast_via_api(self, base_url="http://localhost:8000/prometheus/predict"):
        try:
            response = requests.get(base_url)
            response.raise_for_status()
            data = response.json()
            if "predictions" in data and len(data["predictions"]) > 0:
                return data["predictions"][0]  # 最新予測1件を返す
            return {}
        except Exception as e:
            print(f"⚠️ Prometheus API呼び出し失敗: {e}")
            return {}

    def hold_council(self, market_data: dict) -> dict:
        print("📣 五臣会議を開催します…")

        veritas_result = self.veritas.propose()
        prometheus_forecast = self.get_prometheus_forecast_via_api()
        aurus_decision = self.aurus.process(market_data)
        levia_decision = self.levia.process(market_data)
        noctus_decision = self.noctus.process(market_data)

        decision = aurus_decision if aurus_decision != "HOLD" else levia_decision

        return {
            "final_decision": decision,
            "veritas": veritas_result,
            "prometheus_forecast": prometheus_forecast,
            "aurus": aurus_decision,
            "levia": levia_decision,
            "noctus": noctus_decision,
        }


# 単体テスト（簡易マーケットデータを与える）
if __name__ == "__main__":
    king = KingNoctria()
    mock_market = {
        "price": 1.2530,
        "previous_price": 1.2510,
        "volume": 160,
        "spread": 0.012,
        "order_block": 0.4,
        "volatility": 0.18,
        "trend_prediction": "bullish",
        "sentiment": 0.7,
        "trend_strength": 0.6,
        "liquidity_ratio": 1.1,
        "momentum": 0.8,
        "short_interest": 0.3
    }
    result = king.hold_council(mock_market)
    print("👑 王の判断:", result["final_decision"])
