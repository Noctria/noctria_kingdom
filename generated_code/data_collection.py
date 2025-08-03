import ccxt
import pandas as pd
import os
from path_config import get_path

def fetch_market_data() -> None:
    try:
        exchange = ccxt.binance()
        data = exchange.fetch_ohlcv('USD/JPY', timeframe='1m')
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        storage_path = get_path('trading')
        df.to_csv(os.path.join(storage_path, 'market_data.csv'), index=False)
    except ccxt.NetworkError as e:
        print(f"Network error occurred: {e}")
    except ccxt.ExchangeError as e:
        print(f"Exchange error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

fetch_market_data()
python
