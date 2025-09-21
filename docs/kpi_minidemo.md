#### 📂 src/plan_data/kpi_minidemo.py
```python
# -*- coding: utf-8 -*-
"""
ダミー戦略を読み込み、KPI計算まで通す最小構成版
- 実データ収集やモデル推論は行わず、固定のダミー値を返す
- STRATEGIES_DIR を path_config から取得
"""

import sys
import pandas as pd
from pathlib import Path

# --- STRATEGIES_DIR 解決 ---
try:
    from src.core.path_config import STRATEGIES_DIR
except ImportError:
    raise RuntimeError("path_config が見つからないため終了します")

print(f"📂 Strategies directory = {STRATEGIES_DIR}")

# --- ダミー戦略クラス ---
class DummyStrategy:
    def __init__(self, name):
        self.name = name

    def backtest(self):
        """ダミーのバックテスト結果を返す"""
        return pd.DataFrame([
            {"date": "2025-08-01", "trades": 10, "win_rate": 0.6, "max_dd": -0.05, "pnl": 1200},
            {"date": "2025-08-02", "trades": 12, "win_rate": 0.55, "max_dd": -0.04, "pnl": 900},
            {"date": "2025-08-03", "trades": 8, "win_rate": 0.70, "max_dd": -0.03, "pnl": 1500},
        ])

# --- KPI計算 ---
def calculate_kpis(df: pd.DataFrame) -> dict:
    """与えられたバックテスト結果からKPIを計算"""
    total_trades = df["trades"].sum()
    avg_win_rate = df["win_rate"].mean() * 100
    avg_max_dd = df["max_dd"].mean() * 100
    total_pnl = df["pnl"].sum()
    return {
        "total_trades": total_trades,
        "avg_win_rate(%)": round(avg_win_rate, 2),
        "avg_max_dd(%)": round(avg_max_dd, 2),
        "total_pnl": total_pnl
    }

if __name__ == "__main__":
    strat = DummyStrategy("Demo_Strategy")
    bt_results = strat.backtest()
    kpis = calculate_kpis(bt_results)

    print("📊 Backtest results:")
    print(bt_results)
    print("\n✅ Calculated KPIs:")
    for k, v in kpis.items():
        print(f"  {k}: {v}")
```

---
