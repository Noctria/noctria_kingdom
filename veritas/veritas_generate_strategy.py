import os
from datetime import datetime

# 保存先ディレクトリ
OUTPUT_DIR = "/mnt/e/noctria-kingdom-main/strategies/veritas_generated"

# Veritasが生成した戦略テンプレート（simulate関数付き）
STRATEGY_TEMPLATE = """\
import pandas as pd
import numpy as np

def simulate(data: pd.DataFrame) -> float:
    \"""
    RSIとspreadに基づいたシンプルな戦略
    BUY: RSI > 50 and spread < 2
    SELL: RSI < 50 or spread > 2
    \"""
    capital = 1_000_000  # 初期資本
    position = 0
    entry_price = 0

    for i in range(1, len(data)):
        rsi = data.loc[i, 'RSI(14)']
        spread = data.loc[i, 'spread']
        price = data.loc[i, 'price']

        if position == 0 and rsi > 50 and spread < 2:
            position = capital / price
            entry_price = price

        elif position > 0 and (rsi < 50 or spread > 2):
            capital = position * price
            position = 0

    # ポジションが残っていれば決済
    if position > 0:
        capital = position * data.iloc[-1]['price']

    return capital
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
