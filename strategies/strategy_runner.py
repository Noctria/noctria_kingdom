from strategy_optimizer import select_best_strategy, strategies_performance
from custom_metrics_strategy import custom_metrics_strategy
from liquidity_based_strategy import liquidity_adjusted_strategy
from extended_data_strategy import extended_data_strategy

def run_optimal_strategy(market_data):
    """最適な戦略を適用"""
    best_strategy = select_best_strategy(strategies_performance)

    if best_strategy == "custom_metrics":
        return custom_metrics_strategy(market_data)
    elif best_strategy == "liquidity_based":
        return liquidity_adjusted_strategy(market_data)
    elif best_strategy == "extended_data":
        return extended_data_strategy(market_data)
    else:
        market_data["strategy_signal"] = "HOLD"
        return market_data
