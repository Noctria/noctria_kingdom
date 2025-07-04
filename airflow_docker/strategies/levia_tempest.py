import numpy as np
import pandas as pd
from data.market_data_fetcher import MarketDataFetcher
from core.risk_manager import RiskManager
from core.logger import setup_logger  # 👑 ロガー追加

class LeviaTempest:
    """⚡ スキャルピング戦略を適用する高速トレードAI（MetaAI改修版）"""

    def __init__(self, threshold=0.05, min_liquidity=120, max_spread=0.018):
        self.threshold = threshold
        self.min_liquidity = min_liquidity
        self.max_spread = max_spread
        self.market_fetcher = MarketDataFetcher()
        self.logger = setup_logger("LeviaLogger", "/opt/airflow/logs/LeviaLogger.log")

        # ✅ ヒストリカルデータ取得（1時間足・1ヶ月分）
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")
        if data_array is None:
            self.logger.warning("⚠️ データ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        # ✅ RiskManagementに渡す
        self.risk_manager = RiskManagement(historical_data=historical_data)

    def process(self, market_data):
        """
        市場データを分析し、短期トレード戦略を決定
        """
        if not isinstance(market_data, dict):
            self.logger.warning("⚠️ market_dataがdictでないため、空辞書に置換します")
            market_data = {}

        price_change = self._calculate_price_change(market_data)
        liquidity = market_data.get("volume", 0.0)
        spread = market_data.get("spread", 0.0)
        order_block_impact = market_data.get("order_block", 0.0)
        volatility = market_data.get("volatility", 0.0)

        adjusted_threshold = self.threshold * (1 + order_block_impact)

        # 条件による判定
        if liquidity < self.min_liquidity:
            self.logger.info(f"🛑 Levia: 流動性不足 ({liquidity} < {self.min_liquidity}) により HOLD")
            return "HOLD"

        if spread > self.max_spread:
            self.logger.info(f"🛑 Levia: スプレッド過大 ({spread:.4f} > {self.max_spread}) により HOLD")
            return "HOLD"

        if price_change > adjusted_threshold and volatility < 0.2:
            self.logger.info(f"⚡ Leviaの決断: BUY（Δ={price_change:.4f}, Vol={volatility:.2f}）")
            return "BUY"
        elif price_change < -adjusted_threshold and volatility < 0.2:
            self.logger.info(f"⚡ Leviaの決断: SELL（Δ={price_change:.4f}, Vol={volatility:.2f}）")
            return "SELL"
        else:
            self.logger.info(f"⚖️ Levia: HOLD（Δ={price_change:.4f}, Vol={volatility:.2f}）")
            return "HOLD"

    def _calculate_price_change(self, market_data):
        """価格変動計算"""
        price = market_data.get("price", 0.0)
        previous_price = market_data.get("previous_price", 0.0)
        return price - previous_price

# ✅ テスト実行用ブロック
if __name__ == "__main__":
    levia_ai = LeviaTempest()
    mock_market_data = {
        "price": 1.2050, "previous_price": 1.2040,
        "volume": 150, "spread": 0.012, "order_block": 0.4,
        "volatility": 0.15
    }
    decision = levia_ai.process(mock_market_data)
    print(f"⚔️ Levia（戦術AI）の決断: {decision}")
