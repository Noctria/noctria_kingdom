import random

def simulate_trade(action, volume, spread=0.01, swap=-0.1, commission=-0.05):
    """
    モックの取引結果を生成する例（ロット調整・手数料考慮版）
    """
    if action == "BUY":
        price_change = random.uniform(-0.1, 0.3)
    elif action == "SELL":
        price_change = random.uniform(-0.3, 0.1)
    else:
        return 0.0

    trade_profit = (price_change * volume) - (abs(swap) + abs(commission))
    return round(trade_profit, 4)

if __name__ == "__main__":
    result = simulate_trade("BUY", 1.0)
    print("Simulated Trade Result:", result)
