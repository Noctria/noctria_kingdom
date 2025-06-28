import time
import numpy as np
import pandas as pd

class StressTest:
    """高頻度データ下でのシステム動作をチェックするモジュール"""

    def __init__(self, test_duration=60, tick_rate=0.001):
        self.test_duration = test_duration
        self.tick_rate = tick_rate
        self.data = pd.DataFrame(columns=["timestamp", "price", "volume"])

    def simulate_market_data(self):
        """高頻度市場データを生成し、システム負荷を検証"""
        start_time = time.time()
        while time.time() - start_time < self.test_duration:
            timestamp = time.time()
            price = np.random.uniform(1.2, 1.5)
            volume = np.random.randint(100, 10000)
            self.data = pd.concat([self.data, pd.DataFrame([[timestamp, price, volume]], 
                                                            columns=self.data.columns)], ignore_index=True)
            time.sleep(self.tick_rate)
        return self.data

# ✅ 負荷検証テスト
if __name__ == "__main__":
    stress_tester = StressTest(test_duration=10, tick_rate=0.002)
    simulated_data = stress_tester.simulate_market_data()
    print("Simulated High-Frequency Market Data:\n", simulated_data.head())
