import logging
import torch
import numpy as np
import tensorflow as tf  # TensorFlow を追加

# ✅ GPU メモリの使用を制限（段階的に確保する設定）
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(f"GPU メモリ設定エラー: {e}")

from strategies.Aurus_Singularis import AurusSingularis
from strategies.Levia_Tempest import LeviaTempest
from strategies.Noctus_Sentinella import NoctusSentinella
from strategies.Prometheus_Oracle import PrometheusOracle
from data.data_loader import MarketDataFetcher
from core.risk_management import RiskManager

class Noctria:
    """市場適応型アンサンブルAIトレーダー（王 + EA４人衆統合）"""

    def __init__(self):
        self.logger = logging.getLogger("Noctria")
        self.market_fetcher = MarketDataFetcher(api_key="YOUR_API_KEY")
        self.risk_manager = RiskManager()

        # EA統合
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.prometheus = PrometheusOracle()

    def analyze_market(self):
        """市場データを取得・分析し、EAを統括"""
        market_data = self.market_fetcher.fetch_data()
        if not market_data:
            return None

        risk_evaluation = self.risk_manager.calculate_var([market_data["price_change"]])

        # EA戦略適用
        trend_strategy = self.aurus.process(market_data)
        scalping_strategy = self.levia.process(market_data)
        risk_decision = self.noctus.process(market_data)
        market_forecast = self.prometheus.predict_market(market_data)

        # 最適戦略の決定
        optimal_strategy = self.finalize_strategy(trend_strategy, scalping_strategy, risk_decision, market_forecast)

        return market_data, risk_evaluation, optimal_strategy

    def finalize_strategy(self, trend, scalping, risk, forecast):
        """市場環境に応じた最適戦略の選定"""
        if risk == "AVOID_TRADING":
            return "HOLD"
        if trend == "BUY" and forecast > 0:
            return "BUY"
        if scalping == "SELL":
            return "SELL"
        return "HOLD"

    def execute_trade(self):
        """市場分析結果を元に、EAの最適戦略を適用"""
        market_data, risk_evaluation, optimal_strategy = self.analyze_market()
        if not market_data:
            return "Market analysis failed."

        self.logger.info(f"Executing trade using strategy: {optimal_strategy}")
        return f"Executing trade using: {optimal_strategy}"

# ✅ Noctria AIの起動
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    noctria_ai = Noctria()
    trade_decision = noctria_ai.execute_trade()
    print(trade_decision)
