import os
import sys
import json
import importlib.util
from pathlib import Path
import pandas as pd

# ========================================
# ⚔️ Veritas戦略 → EA命令JSON生成スクリプト
# ========================================

# ✅ 正しいMT5の "Files" ディレクトリに出力
SIGNAL_OUTPUT_PATH = Path(
    "/mnt/c/Users/masay/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files/veritas_signal.json"
)
STRATEGY_PATH = Path("strategies/official/")
TARGET_STRATEGY = "sample_strategy.py"  # 実行対象戦略（任意に変更可）

# 🗃 ダミー市場データ
def load_dummy_market_data():
    dates = pd.date_range(start="2025-01-01", periods=100, freq="H")
    data = pd.DataFrame({
        "Open": 1.0,
        "High": 1.1,
        "Low": 0.9,
        "Close": 1.0,
    }, index=dates)
    return data

# 🔄 simulate関数のロード
def load_simulate_function(filepath):
    spec = importlib.util.spec_from_file_location("strategy_module", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.simulate

# 🧠 シグナル抽出
def extract_signal(result_dict):
    return {
        "signal": result_dict.get("signal", "BUY"),
        "symbol": result_dict.get("symbol", "USDJPY"),
        "lot": result_dict.get("lot", 0.1),
        "tp": result_dict.get("tp", 10),
        "sl": result_dict.get("sl", 8),
    }

# ✅ メイン処理
def main():
    strategy_file = STRATEGY_PATH / TARGET_STRATEGY
    if not strategy_file.exists():
        print("❌ 戦略ファイルが見つかりません:", strategy_file)
        return

    simulate = load_simulate_function(strategy_file)
    market_data = load_dummy_market_data()
    result = simulate(market_data)

    signal = extract_signal(result)

    # 💾 JSON出力
    SIGNAL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SIGNAL_OUTPUT_PATH, "w") as f:
        json.dump(signal, f, indent=2)

    print("✅ EA命令ファイルを出力しました:", SIGNAL_OUTPUT_PATH)
    print("📦 内容:", signal)

if __name__ == "__main__":
    main()
