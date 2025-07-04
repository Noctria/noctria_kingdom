from tradingview_fetcher import process_tradingview_data
from strategy_optimizer import select_best_strategy, strategies_performance

def apply_tradingview_strategy(data):
    """TradingView市場データを活用し、戦略適用"""
    processed_data = process_tradingview_data(data)
    best_strategy = select_best_strategy(strategies_performance)

    processed_data["strategy_signal"] = "HOLD"

    # 戦略の選定
    if best_strategy == "custom_metrics":
        rsi_value = processed_data["RSI(14)"].iloc[-1]
        atr_value = processed_data["ATR(14)"].iloc[-1]  # 追加
        trend_sma = processed_data["SMA(50)"].iloc[-1]  # 追加
        
        if rsi_value > 50 and trend_sma > processed_data["price"].iloc[-1] and atr_value < 1.5:
            processed_data["strategy_signal"] = "BUY"
        elif rsi_value < 50 and trend_sma < processed_data["price"].iloc[-1] and atr_value < 1.5:
            processed_data["strategy_signal"] = "SELL"

    elif best_strategy == "liquidity_based":
        spread_value = processed_data["spread"].iloc[-1]
        liquidity_value = processed_data["liquidity"].iloc[-1]  # 追加

        if spread_value < 2 and liquidity_value > 100:
            processed_data["strategy_signal"] = "BUY"
        elif spread_value > 2 and liquidity_value < 100:
            processed_data["strategy_signal"] = "SELL"

    return processed_data
