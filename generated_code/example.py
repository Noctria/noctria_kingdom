import pandas as pd  # pandasはデータ処理や操作に強力なツールを提供します

def fetch_market_data():
    # Binance取引所のインスタンスを作成します
    exchange = ccxt.binance()
    
    # 'USD/JPY'ペアの1分足のOHLCVデータを取得します
    data = exchange.fetch_ohlcv('USD/JPY', timeframe='1m')
    

    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    

    df.to_csv('market_data.csv', index=False)

fetch_market_data()
