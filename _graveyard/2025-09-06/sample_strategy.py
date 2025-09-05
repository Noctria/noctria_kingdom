from datetime import datetime
import pandas as pd

def simulate(data: pd.DataFrame):
    """
    本戦略のエントリーポイント関数。
    Noctria王による統合判断に利用される形式で結果を返す。
    
    引数:
        data (pd.DataFrame): 市場データ（Open, High, Low, Closeなど）

    戻り値:
        dict: 発注判断および指示
    """
    # 簡易なBUY判定ロジック（デモ用）
    latest_price = data["Close"].iloc[-1]
    signal = "BUY" if latest_price > 0.99 else "SELL"

    return {
        "signal": signal,
        "symbol": "USDJPY",
        "lot": 0.1,
        "tp": 10,
        "sl": 8,
        "confidence": 0.87,
        "timestamp": datetime.utcnow().isoformat()
    }
