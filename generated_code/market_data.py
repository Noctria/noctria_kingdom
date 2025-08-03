import pandas as pd
import random

def get_market_data(pair):
    print(f"Retrieving market data for {pair}")
    # APIからのデータ取得を仮定、実際にはライブラリを利用した外部API連携などが必要
    data = pd.DataFrame({
        'Date': pd.date_range(start='2023-01-01', periods=100),
        'Close': [100 + random.gauss(0, 1) for _ in range(100)]
    })
    return data
python
