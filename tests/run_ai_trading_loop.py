# run_ai_trading_loop.py
import time
import requests
from order_execution import OrderExecution  # Docker/Linux 側クラス
from ai_strategies.noctria_master_ai import NoctriaMasterAI  # AI戦略層
from data.market_data_fetcher import MarketDataFetcher  # データ取得層

# 各コンポーネント初期化
fetcher = MarketDataFetcher()
ai_strategy = NoctriaMasterAI()
executor = OrderExecution(api_url="http://192.168.11.30:5001/order")

while True:
    # 1️⃣ 最新市場データ取得
    market_data = fetcher.get_usdjpy_latest_price()
    print("最新市場データ:", market_data)

    # 2️⃣ AI戦略の判定
    ai_output = ai_strategy.analyze_market(market_data)
    print("NoctriaMasterAI 出力:", ai_output)

    # 3️⃣ エントリー条件チェック（"buy" or "sell"）
    action = ai_output.get("action")
    if action in ["buy", "sell"]:
        symbol = ai_output.get("symbol", "USDJPY")
        lot = ai_output.get("lot", 0.1)

        # 4️⃣ Windows側MT5サーバーに注文送信
        order_result = executor.execute_order(symbol, lot, order_type=action)
        print("注文結果:", order_result)
    else:
        print("取引しない（HOLD判定）")

    # 5️⃣ ループ間隔（例: 10秒ごと）
    time.sleep(10)
