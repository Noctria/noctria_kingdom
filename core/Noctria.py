import logging
import numpy as np
import pandas as pd

from strategies.Aurus_Singularis import AurusSingularis
from strategies.Levia_Tempest import LeviaTempest
from strategies.Noctus_Sentinella import NoctusSentinella
from strategies.Prometheus_Oracle import PrometheusOracle
from strategies.NoctriaMasterAI import NoctriaMasterAI
from data.market_data_fetcher import MarketDataFetcher
from core.risk_management import RiskManagement


class Noctria:
    """市場適応型アンサンブルAIトレーダー（王 + EA４人衆 + AI戦略層）"""

    def __init__(self):
        self.logger = logging.getLogger("Noctria")

        # ✅ MarketDataFetcherでヒストリカルデータ取得
        self.market_fetcher = MarketDataFetcher()
        data_array = self.market_fetcher.get_usdjpy_historical_data(interval="1h", period="1mo")

        if data_array is None:
            # データ取得に失敗したらダミーデータで初期化
            self.logger.warning("⚠️ ヒストリカルデータ取得失敗。ダミーデータで初期化します")
            data_array = np.random.normal(loc=100, scale=5, size=(100, 5))

        columns = ["Open", "High", "Low", "Close", "Volume"]
        historical_data = pd.DataFrame(data_array, columns=columns)

        # ✅ RiskManagementにhistorical_dataを渡す
        self.risk_manager = RiskManagement(historical_data=historical_data)

        # EA戦略4人衆
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.prometheus = PrometheusOracle()

        # ✅ AI戦略層の統合クラス
        self.ai_env = NoctriaMasterAI()

    def analyze_market(self):
        """市場データ取得→AI戦略層分析→EA統合戦略決定"""
        market_data = {
            "historical_prices": self.risk_manager.data,  # DataFrame形式で渡す
            "price_change": 0.05  # 例としてダミー値
        }

        # ✅ AI戦略層にデータを渡して総合AI結果を取得
        ai_output = self.ai_env.analyze_market({
            "observation": self._create_observation_vector(market_data),
            "historical_prices": market_data["historical_prices"].values,
            "price_change": market_data["price_change"]
        })

        self.logger.debug(f"AI戦略層の出力: {ai_output}")

        # EA戦略の適用
        trend_strategy = self.aurus.process(market_data)
        scalping_strategy = self.levia.process(market_data)
        risk_decision = self.noctus.process(market_data)
        market_forecast = self.prometheus.predict_market(market_data)

        # ✅ AI戦略のスコア・リスクレベルも最終戦略決定に加味
        optimal_strategy = self.finalize_strategy(
            trend_strategy,
            scalping_strategy,
            risk_decision,
            market_forecast,
            ai_output
        )

        return market_data, ai_output, optimal_strategy

    def finalize_strategy(self, trend, scalping, risk, forecast, ai_output):
        """AI戦略層の結果 + EA戦略4人衆の結果を統合し、最適戦略を決定"""
        if ai_output["risk_level"] == "REDUCE_POSITION" or risk == "AVOID_TRADING":
            return "HOLD"

        if ai_output["lstm_score"] > 0.6:
            return "BUY"
        elif ai_output["lstm_score"] < 0.4:
            return "SELL"

        if trend == "BUY" and forecast > 0:
            return "BUY"
        if scalping == "SELL":
            return "SELL"

        return "HOLD"

    def _create_observation_vector(self, market_data):
        """
        EA戦略などの結果から12次元の観測ベクトルを作成する例。
        本格的には、より高度な特徴量も含めて拡張できる。
        """
        obs = [market_data.get("price_change", 0.0)] * 12
        return obs

    def execute_trade(self):
        """分析結果に基づいて最終的な戦略でトレード実行"""
        result = self.analyze_market()
        if not result:
            return "Market analysis failed."

        _, ai_output, optimal_strategy = result
        self.logger.info(f"Executing trade using optimal strategy: {optimal_strategy}")
        return f"Executing trade using: {optimal_strategy}"


# ✅ Noctria AIのテスト起動例
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    noctria_ai = Noctria()
    trade_decision = noctria_ai.execute_trade()
    print(trade_decision)
