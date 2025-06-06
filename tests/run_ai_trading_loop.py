# tests/run_ai_trading_loop.py

import time
import sys
import os
import numpy as np

# ✅ プロジェクトルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# execution/ ディレクトリ
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'execution')))
from order_execution import OrderExecution

# strategies/ ディレクトリ
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'strategies')))
from NoctriaMasterAI import NoctriaMasterAI

# data/ ディレクトリ
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data')))
from market_data_fetcher import MarketDataFetcher

# 各コンポーネント初期化
fetcher = MarketDataFetcher()
ai_strategy = NoctriaMasterAI()
executor = OrderExecution(api_url="http://192.168.11.30:5001/order")

while True:
    # 1️⃣ 最新市場データ取得（例: ドル円レートだけ取得）
    latest_price = fetcher.get_usdjpy_latest_price()
    print("最新取得レート:", latest_price)

    # 2️⃣ 必要な形に変換（AIに渡す辞書形式に統一）
    market_data = {
        "observation": np.array([latest_price] * 12),      # 例: 観測データを価格で埋める
        "historical_prices": np.random.rand(100, 5),      # 例: ダミーの過去データ
        "price_change": np.random.randn() * 0.01          # 例: ダミーの変動率
    }

    # 3️⃣ AI戦略で分析
    ai_output = ai_strategy.analyze_market(market_data)
    print("NoctriaMasterAI 出力:", ai_output)

    # 4️⃣ エントリー条件判定
    action = ai_output.get("action")
    if action in ["buy", "sell"]:
        symbol = ai_output.get("symbol", "USDJPY")
        lot = ai_output.get("lot", 0.1)

        # 5️⃣ Windows側MT5サーバーに発注
        order_result = executor.execute_order(symbol, lot, order_type=action)
        print("注文結果:", order_result)
    else:
        print("取引しない（HOLD判定）")

    # 6️⃣ ループ間隔（例: 10秒）
    time.sleep(10)
