# strategies/official/sample_strategy.py

from datetime import datetime

def simulate():
    """
    本戦略のエントリーポイント関数。
    Noctria王による統合判断に利用される形式で結果を返す。
    """
    decision = {
        "action": "buy",               # または "sell", "hold"
        "confidence": 0.87,            # 戦略の信頼度（0〜1）
        "timestamp": datetime.utcnow().isoformat()
    }
    return decision
