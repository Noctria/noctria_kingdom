from tradingview_fetcher import process_tradingview_data
from strategy_optimizer import select_best_strategy, strategies_performance

def apply_tradingview_strategy(data):
    """TradingView市場データを活用し、戦略適用"""
    processed_data = process_tradingview_data(data)
    best_strategy = select_best_strategy(strategies_performance)

    processed_data["strategy_signal"] = "HOLD"

    if best_strategy == "custom_metrics":
        processed_data["strategy_signal"] = "BUY" if processed_data["RSI(14)"].iloc[-1] > 50 else "SELL"
    elif best_strategy == "liquidity_based":
        processed_data["strategy_signal"] = "BUY" if processed_data["spread"].iloc[-1] < 2 else "SELL"
    
    return processed_data
