# test_mt5_connection.py
import MetaTrader5 as mt5

# MT5起動確認
if not mt5.initialize():
    print("MT5 initialize() failed")
    mt5.shutdown()
else:
    print("MT5 initialize() successful")

    # 口座情報の取得
    account_info = mt5.account_info()
    if account_info is not None:
        print("Account Info:")
        print(account_info._asdict())
    else:
        print("Failed to get account info")

    # USDJPYの現在価格取得テスト
    symbol = "USDJPY"
    tick = mt5.symbol_info_tick(symbol)
    if tick is not None:
        print(f"Current {symbol} price: Bid={tick.bid}, Ask={tick.ask}")
    else:
        print(f"Failed to get {symbol} price")

    mt5.shutdown()
