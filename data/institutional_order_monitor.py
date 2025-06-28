import numpy as np
import pandas as pd

class InstitutionalOrderMonitor:
    """機関投資家の注文動向を監視し、市場への影響を分析"""
    
    def __init__(self, threshold=1000000):
        self.threshold = threshold  # 大口注文の基準額
    
    def detect_large_orders(self, order_flow_data):
        """大量注文を検出し、市場の流動性へ影響を評価"""
        large_orders = order_flow_data[order_flow_data["order_size"] > self.threshold]
        return large_orders

# ✅ 機関注文監視テスト
if __name__ == "__main__":
    mock_orders = pd.DataFrame({"order_size": np.random.randint(500000, 2000000, 50)})
    monitor = InstitutionalOrderMonitor()
    detected_orders = monitor.detect_large_orders(mock_orders)
    print("Detected Large Orders:\n", detected_orders)
