import pandas as pd
import numpy as np

def simulate(data: pd.DataFrame) -> dict:
    """
    RSIとspreadに基づいたシンプルな戦略
    BUY: RSI > 50 and spread < 2
    SELL: RSI < 50 or spread > 2

    戻り値:
        {
            "final_capital": float,
            "win_rate": float,
            "max_drawdown": float,
            "total_trades": int
        }
    """
    capital = 1_000_000  # 初期資本
    balance = capital
    position = 0
    entry_price = 0
    trades = []
    equity_curve = []

    for i in range(1, len(data)):
        rsi = data.loc[i, 'RSI(14)']
        spread = data.loc[i, 'spread']
        price = data.loc[i, 'price']

        if position == 0 and rsi > 50 and spread < 2:
            position = balance / price
            entry_price = price

        elif position > 0 and (rsi < 50 or spread > 2):
            exit_price = price
            pnl = position * (exit_price - entry_price)
            trades.append(pnl)
            balance += pnl
            position = 0

        equity_curve.append(balance if position == 0 else position * price)

    if position > 0:
        final_price = data.iloc[-1]['price']
        pnl = position * (final_price - entry_price)
        trades.append(pnl)
        balance += pnl
        equity_curve.append(balance)

    total_trades = len(trades)
    win_trades = len([t for t in trades if t > 0])
    win_rate = win_trades / total_trades if total_trades > 0 else 0.0

    # 最大ドローダウン計算
    equity_series = pd.Series(equity_curve)
    peak = equity_series.cummax()
    drawdown = (equity_series - peak) / peak
    max_drawdown = drawdown.min() if not drawdown.empty else 0.0

    return {
        "final_capital": balance,
        "win_rate": round(win_rate, 4),
        "max_drawdown": round(abs(max_drawdown), 4),
        "total_trades": total_trades
    }
