import logging
from strategies import Aurus_Singularis, Levia_Tempest, Noctus_Sentinella, Prometheus_Oracle

class Noctria:
    """Noctria Kingdom全体を統括するAI管理モジュール"""
    
    def __init__(self):
        self.strategies = {
            "trend_analysis": Aurus_Singularis(),
            "scalping": Levia_Tempest(),
            "risk_management": Noctus_Sentinella(),
            "market_prediction": Prometheus_Oracle(),
        }
        self.logger = logging.getLogger("Noctria")
        self.logger.setLevel(logging.INFO)
    
    def execute_strategy(self, market_data):
        """各戦略を適用し、最適なトレード判断を導出"""
        results = {}
        for name, strategy in self.strategies.items():
            results[name] = strategy.process(market_data)
            self.logger.info(f"{name} strategy executed.")
        
        optimal_decision = self.optimize_trade(results)
        return optimal_decision
    
    def optimize_trade(self, strategy_results):
        """各戦略の結果を統合し、最適な意思決定を行う"""
        best_choice = max(strategy_results, key=strategy_results.get)
        self.logger.info(f"Optimal strategy chosen: {best_choice}")
        return best_choice

# ✅ Noctria AIの起動
if __name__ == "__main__":
    noctria_ai = Noctria()
    mock_market_data = {"price": 1.2345, "volume": 1000}
    decision = noctria_ai.execute_strategy(mock_market_data)
    print("Final Decision:", decision)
