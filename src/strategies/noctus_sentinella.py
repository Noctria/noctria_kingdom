import numpy as np
import pandas as pd
from core.data.market_data_fetcher import MarketDataFetcher
from core.risk_manager import RiskManager

class NoctusSentinella:
    """
    🛡️ Noctria Kingdomの守護者：リスク管理と異常検知を担う戦略AI。
    - ヒストリカルデータを用いてVaRベースの評価を行い、
      市場流動性やボラティリティを加味して意思決定を行う。
    """

    def __init__(self, risk_threshold=0.02, max_spread=0.018, min_liquidity=120):
        self.risk_threshold = risk_threshold
        self.max_spread = max_spread
        self.min_liquidity = min_liquidity
        self.market_fetcher = MarketDataFetcher()

        # ✅ ヒストリカルデータ取得（1時間足・1ヶ月分）
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            print("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        # ✅ リスク管理AIにヒストリカルデータを渡す
        self.risk_manager = RiskManager(historical_data=historical_data)

    def _calculate_risk(self, market_data):
        """
        VaRを用いたリスクスコア計算（priceに対するVaRの比率）。
        """
        price_history = market_data.get("price_history", [])
        price = market_data.get("price", 1.0)

        if not price_history or price <= 0:
            return 0.0

        try:
            risk_value = self.risk_manager.calculate_var()
            return risk_value / price if risk_value is not None else 0.0
        except Exception as e:
            print(f"[Noctus] ❌ リスク計算失敗: {e}")
            return 0.0

    def process(self, market_data):
        """
        市場データを分析し、リスクを評価する。
        ➜ データ不備時には防御的対応。
        """
        if not isinstance(market_data, dict):
            print("⚠️ market_dataがlistなどで渡されました。空辞書に置換します")
            market_data = {}

        risk_score = self._calculate_risk(market_data)
        spread = market_data.get("spread", 0.0)
        liquidity = market_data.get("volume", 0.0)
        order_block_impact = market_data.get("order_block", 0.0)
        volatility = market_data.get("volatility", 0.0)

        adjusted_risk_threshold = self.risk_threshold * (1 + order_block_impact)

        print(f"[Noctus] risk_score={risk_score:.5f}, threshold={adjusted_risk_threshold:.5f}, volatility={volatility:.3f}")

        if liquidity < self.min_liquidity or spread > self.max_spread:
            print("[Noctus] 🚫 流動性不足 or スプレッド高 → 回避")
            return "AVOID_TRADING"

        if risk_score > adjusted_risk_threshold and volatility > 0.2:
            return "REDUCE_RISK"
        else:
            return "MAINTAIN_POSITION"

    def propose(self, market_data: dict) -> dict:
        """
        📩 王Noctriaへの献上：リスク状況の提言を返す
        """
        risk_score = self._calculate_risk(market_data)
        spread = market_data.get("spread", 0.0)
        liquidity = market_data.get("volume", 0.0)
        volatility = market_data.get("volatility", 0.0)
        order_block_impact = market_data.get("order_block", 0.0)
        adjusted_threshold = self.risk_threshold * (1 + order_block_impact)

        if liquidity < self.min_liquidity or spread > self.max_spread:
            signal = "AVOID_TRADING"
        elif risk_score > adjusted_threshold and volatility > 0.2:
            signal = "REDUCE_RISK"
        else:
            signal = "MAINTAIN_POSITION"

        score = round(risk_score, 4)

        return {
            "name": "Noctus",
            "type": "risk_management",
            "signal": signal,
            "score": score,
            "symbol": market_data.get("symbol", "USDJPY"),
            "priority": "critical"
        }

# ✅ 単体テスト
if __name__ == "__main__":
    noctus_ai = NoctusSentinella()
    mock_market_data = {
        "price": 1.2530,
        "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540],
        "spread": 0.015,
        "volume": 120,
        "order_block": 0.5,
        "volatility": 0.22,
        "symbol": "USDJPY"
    }
    result = noctus_ai.propose(mock_market_data)
    print("🧠 王への提案（Noctus）:", result)
