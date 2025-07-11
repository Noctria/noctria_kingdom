import numpy as np
import pandas as pd
import traceback
from core.risk_control import RiskControl

def load_market_data(csv_file='market_data.csv'):
    try:
        df = pd.read_csv(csv_file, parse_dates=['Date'])
        df.sort_values('Date', inplace=True)
        prices = df['Close'].values
        print(f"CSVから{len(prices)}件の価格データを取得しました。")
        return prices
    except Exception as e:
        print("CSVの読み込みに失敗しました:", e)
        return None

def simulate_strategy_adjusted(prices, entry_threshold, exit_threshold, initial_capital=1000000):
    risk_control = RiskControl(initial_capital)
    position = 0
    shares = 0
    buy_price = None

    for i in range(1, len(prices)):
        _, _, active = risk_control.check_risk()
        if not active:
            print(f"【警告】リスク制御によりシミュレーション終了 (Day {i})")
            return risk_control.current_capital

        daily_return = (prices[i] - prices[i - 1]) / prices[i - 1]

        if position == 0 and daily_return <= -entry_threshold:
            shares = risk_control.current_capital / prices[i]
            buy_price = prices[i]
            position = 1

        elif position == 1 and daily_return >= exit_threshold:
            sell_value = shares * prices[i]
            profit_loss = sell_value - (shares * buy_price)
            risk_control.update_account(profit_loss)
            position = 0
            shares = 0
            buy_price = None

    if position == 1:
        sell_value = shares * prices[-1]
        profit_loss = sell_value - (shares * buy_price)
        risk_control.update_account(profit_loss)

    return risk_control.current_capital

def simulate_strategy_adjusted(strategy_path: str, market_data: pd.DataFrame) -> dict:
    try:
        namespace = {}
        with open(strategy_path, 'r', encoding='utf-8') as f:
            code = f.read()
            exec(code, namespace)

        if 'strategy' not in namespace or not callable(namespace['strategy']):
            return {
                "status": "error",
                "error_message": "strategy関数が定義されていません"
            }

        result = namespace['strategy'](market_data)

        if not isinstance(result, dict):
            return {
                "status": "error",
                "error_message": "strategy関数の返り値がdict型ではありません"
            }

        return {
            "status": "ok",
            "final_capital": result.get("final_capital"),
            "win_rate": result.get("win_rate"),
            "max_drawdown": result.get("max_drawdown"),
            "total_trades": result.get("total_trades"),
            "error_message": None
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": traceback.format_exc()
        }

def optimize_parameters_adjusted(prices, initial_capital=1000000):
    best_profit = -np.inf
    best_params = None

    entry_candidates = np.linspace(0.01, 0.05, 5)
    exit_candidates = np.linspace(0.01, 0.05, 5)

    for entry_threshold in entry_candidates:
        for exit_threshold in exit_candidates:
            profit = simulate_strategy_adjusted(prices, entry_threshold, exit_threshold, initial_capital)
            if profit > best_profit:
                best_profit = profit
                best_params = (entry_threshold, exit_threshold)
                print(f"✅ 最適: entry={entry_threshold:.3f}, exit={exit_threshold:.3f}, profit={profit:.2f}")

    return best_params, best_profit

if __name__ == "__main__":
    prices = load_market_data('market_data.csv')
    if prices is None:
        np.random.seed(42)
        days = 252
        daily_returns = np.random.normal(0, 0.01, days)
        prices = 100 * np.cumprod(1 + daily_returns)
        print("📊 ダミーデータを生成しました")

    best_params, best_profit = optimize_parameters_adjusted(prices)
    print("🎯 最適パラメータ:", best_params)
    print(f"📈 最終資産額: {best_profit:,.0f} 円")
