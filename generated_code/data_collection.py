# ファイル名: data_collection.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T17:09:17.279204
# 生成AI: openai_noctria_dev.py
# UUID: 28c1514f-0ffe-4d6d-ad9b-c6ea9b1f4c16

import ccxt
import pandas as pd
import os

# --- ストレージパスを直接定義（または path_config.py から定数import推奨） ---
STORAGE_PATH = "./local_data/"

def fetch_market_data():
    try:
        exchange = ccxt.binance()
        # 実際のUSD/JPYがなければダミーのBTC/USDTなどに変更
        data = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m')
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        os.makedirs(STORAGE_PATH, exist_ok=True)
        df.to_csv(os.path.join(STORAGE_PATH, 'market_data.csv'), index=False)
    except ccxt.NetworkError as e:
        print(f"Network error occurred: {e}")
    except ccxt.ExchangeError as e:
        print(f"Exchange error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# テストから呼べるよう export
def fetch_forex_data():
    fetch_market_data()

if __name__ == "__main__":
    fetch_market_data()
