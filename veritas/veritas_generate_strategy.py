from core.path_config import *
import os
from datetime import datetime

# 保存先ディレクトリ
OUTPUT_DIR = str(GENERATED_STRATEGIES_DIR)

# Veritasが生成した戦略テンプレート（simulate関数付き・dict対応）
STRATEGY_TEMPLATE = """\
import pandas as pd
import numpy as np

def simulate(data: pd.DataFrame) -> dict:
    \"""
    RSIとspreadに基づいたシンプルな戦略
    BUY: RSI > 50 and spread < 2
    SELL: RSI < 50 or spread > 2
    \"""
    capital = 1_000_000  # 初期資本
    position = 0
    entry_price = 0
    wins = 0
    losses = 0
    capital_history = [capital]

    for i in range(1, len(data)):
        rsi = data.loc[i, 'RSI(14)']
        spread = data.loc[i, 'spread']
        price = data.loc[i, 'price']

        if position == 0 and rsi > 50 and spread < 2:
            position = capital / price
            entry_price = price

        elif position > 0 and (rsi < 50 or spread > 2):
            exit_price = price
            new_capital = position * exit_price
            if new_capital > capital:
                wins += 1
            else:
                losses += 1
            capital = new_capital
            capital_history.append(capital)
            position = 0

    # ポジションが残っていれば決済
    if position > 0:
        capital = position * data.iloc[-1]['price']
        capital_history.append(capital)

    # 指標計算
    total_trades = wins + losses
    win_rate = wins / total_trades if total_trades > 0 else 0.0
    peak = capital_history[0]
    max_drawdown = 0.0

    for val in capital_history:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        max_drawdown = max(max_drawdown, dd)

    return {
        "final_capital": round(capital),
        "win_rate": round(win_rate, 4),
        "max_drawdown": round(max_drawdown, 4),
        "total_trades": total_trades
    }
"""

def generate_strategy_file(strategy_name: str):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{strategy_name}_{timestamp}.py"
    filepath = os.path.join(OUTPUT_DIR, filename)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(filepath, "w") as f:
        f.write(STRATEGY_TEMPLATE)

    print(f"✅ 戦略ファイルを生成しました: {filepath}")
    return filepath

if __name__ == "__main__":
    # 実行時に "veritas_strategy_yyyymmdd_HHMMSS.py" を生成
    generate_strategy_file("veritas_strategy")
