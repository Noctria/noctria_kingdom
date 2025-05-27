import numpy as np

class StrategyRunner:
    """複数の戦略を統合し、最適なトレード決定を導くモジュール"""
    
    def __init__(self, strategies):
        self.strategies = strategies
    
    def execute(self, market_data):
        """各戦略を適用し、最適な判断を導出"""
        results = {}
        for name, strategy in self.strategies.items():
            results[name] = strategy.process(market_data)
        
        optimal_decision = self._aggregate_results(results)
        return optimal_decision

    def _aggregate_results(self, strategy_results):
        """戦略結果を統合し、最終意思決定を行う"""
        decision_counts = {decision: list(strategy_results.values()).count(decision) for decision in set(strategy_results.values())}
        best_choice = max(decision_counts, key=decision_counts.get)
        return best_choice

# ✅ 戦略適用テスト
if __name__ == "__main__":
    from Aurus_Singularis import AurusSingularis
    from Levia_Tempest import LeviaTempest
    from Noctus_Sentinella import NoctusSentinella

    strategies = {
        "trend_analysis": AurusSingularis(),
        "scalping": LeviaTempest(),
        "risk_management": NoctusSentinella(),
    }

    runner = StrategyRunner(strategies)
    mock_market_data = {"price": 1.2500, "previous_price": 1.2480, "price_history": [1.2450, 1.2475, 1.2500]}
    final_decision = runner.execute(mock_market_data)
    print("Final Trading Decision:", final_decision)
