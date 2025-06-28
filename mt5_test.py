import MetaTrader5 as mt5

# MetaTrader5への接続を初期化
if not mt5.initialize():
    print("MetaTrader5の初期化に失敗しました。エラーコード:", mt5.last_error())
    quit()

print("MetaTrader5に接続しました！")

# 口座情報の取得
account_info = mt5.account_info()
if account_info:
    print("口座情報:")
    print(account_info)
else:
    print("口座情報が取得できませんでした。")

# シンボル情報の取得（例：USDJPY）
symbol = "USDJPY"
symbol_info = mt5.symbol_info(symbol)
if symbol_info:
    print(f"{symbol}の情報:")
    print(symbol_info)
else:
    print(f"{symbol}の情報が取得できませんでした。")

# 終了
mt5.shutdown()
print("MetaTrader5を終了しました。")
