import numpy as np
import pandas as pd
from data.market_data_fetcher import MarketDataFetcher
from core.risk_manager import RiskManager
from core.logger import setup_logger  # 👑 ログ追加

class NoctusSentinella:
    """🛡️ リスク管理と異常検知を行うAI（ヒストリカルデータ + MetaAI対応）"""

    def __init__(self, risk_threshold=0.02, max_spread=0.018, min_liquidity=120):
        self.risk_threshold = risk_threshold
        self.max_spread = max_spread
        self.min_liquidity = min_liquidity
        self.logger = setup_logger("NoctusLogger")
        self.market_fetcher = MarketDataFetcher()

        # ✅ ヒストリカルデータ取得
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            self.logger.warning("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)
        self.risk_manager = RiskManager(historical_data=historical_data)

    def process(self, market_data):
        if not isinstance(market_data, dict):
            self.logger.warning("⚠️ market_dataがlistなどで渡されました。空辞書に置換します")
            market_data = {}

        risk_score = self._calculate_risk(market_data)
        spread = market_data.get("spread", 0.0)
        liquidity = market_data.get("volume", 0.0)
        order_block_impact = market_data.get("order_block", 0.0)
        volatility = market_data.get("volatility", 0.0)

        adjusted_threshold = self.risk_threshold * (1 + order_block_impact)

        if liquidity < self.min_liquidity:
            self.logger.info(f"⚠️ Noctus: 流動性不足 ({liquidity} < {self.min_liquidity}) ➜ AVOID_TRADING")
            return "AVOID_TRADING"

        if spread > self.max_spread:
            self.logger.info(f"⚠️ Noctus: スプレッド過大 ({spread:.4f} > {self.max_spread}) ➜ AVOID_TRADING")
            return "AVOID_TRADING"

        if risk_score > adjusted_threshold and volatility > 0.2:
            self.logger.info(f"🛑 Noctus: リスク高（Score={risk_score:.4f} > {adjusted_threshold:.4f}） ➜ REDUCE_RISK")
            return "REDUCE_RISK"
        else:
            self.logger.info(f"✅ Noctus: 許容リスク範囲内（Score={risk_score:.4f}） ➜ MAINTAIN_POSITION")
            return "MAINTAIN_POSITION"

    def _calculate_risk(self, market_data):
        price_history = market_data.get("price_history", [])
        price = market_data.get("price", 1.0)

        if not price_history or price == 0:
            self.logger.warning("⚠️ priceまたはprice_history不足 ➜ Risk=0.0")
            return 0.0

        risk_value = self.risk_manager.value_at_risk
        return risk_value / price

# ✅ テスト用ブロック
if __name__ == "__main__":
    noctus_ai = NoctusSentinella()
    mock_market_data = {
        "price": 1.2530,
        "price_history": [1.2500, 1.2525, 1.2550, 1.2510, 1.2540],
        "spread": 0.015,
        "volume": 120,
        "order_block": 0.5,
        "volatility": 0.22
    }
    decision = noctus_ai.process(mock_market_data)
    print(f"🛡️ Noctus（リスク管理AI）の判断: {decision}")
