# test_mt5_connection.py
import MetaTrader5 as mt5
from datetime import datetime

print("========== MetaTrader5接続テスト ==========")

# 1️⃣ MT5の初期化
if not mt5.initialize():
    print("❌ MT5 initialize() failed")
    mt5.shutdown()
else:
    print("✅ MT5 initialize() successful")

    # 2️⃣ 口座情報の取得
    account_info = mt5.account_info()
    if account_info is not None:
        print("\n=== 口座情報 ===")
        for key, value in account_info._asdict().items():
            print(f"{key}: {value}")
    else:
        print("❌ 口座情報の取得に失敗しました")

    # 3️⃣ シンボルリスト取得テスト
    symbols = mt5.symbols_get()
    if symbols is not None:
        print(f"\n=== 取引可能シンボル: {len(symbols)}件 ===")
        for s in symbols[:10]:  # 先頭10件だけ表示
            print(s.name)
    else:
        print("❌ シンボル取得に失敗しました")

    # 4️⃣ USDJPYの価格取得テスト
    symbol = "USDJPY"
    tick = mt5.symbol_info_tick(symbol)
    if tick is not None:
        print(f"\n=== {symbol}の現在価格 ===")
        print(f"Bid: {tick.bid}")
        print(f"Ask: {tick.ask}")
    else:
        print(f"❌ {symbol}の価格取得に失敗しました")

    # 5️⃣ テスト買い注文（0.1ロットの成行注文）
    lot = 0.1
    point = mt5.symbol_info(symbol).point
    price = tick.ask
    deviation = 20  # 許容スリッページ

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "sl": price - 50 * point,  # 50ポイント下にSL
        "tp": price + 50 * point,  # 50ポイント上にTP
        "deviation": deviation,
        "magic": 123456,
        "comment": "test order from test_mt5_connection.py",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    print("\n=== 注文リクエスト ===")
    print(request)

    result = mt5.order_send(request)
    print("\n=== 注文結果 ===")
    print(result)

    # 6️⃣ MT5のシャットダウン
    mt5.shutdown()
