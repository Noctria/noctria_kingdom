import os
import sys
import json
import importlib.util
from pathlib import Path
import pandas as pd

# ========================================
# ⚔️ Veritas戦略 → EA命令JSON生成スクリプト
# ========================================

# 📌 設定（Windows側共有ディレクトリに出力）
SIGNAL_OUTPUT_PATH = Path("/mnt/d/MT5_shared/veritas_signal.json")
STRATEGY_PATH = Path("strategies/official/")  # 昇格戦略の格納場所
TARGET_STRATEGY = "strategy_001.py"           # 実行対象戦略（ファイル名）

# 🗃 市場データ（簡易ダミーで可）
def load_dummy_market_data():
    dates = pd.date_range(start="2025-01-01", periods=100, freq="H")
    data = pd.DataFrame({
        "Open": 1.0,
        "High": 1.1,
        "Low": 0.9,
        "Close": 1.0,
    }, index=dates)
    return data

# 🔄 動的インポート（simulate関数を取得）
def load_simulate_function(filepath):
    spec = importlib.util.spec_from_file_location("strategy_module", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.simulate

# 🧠 戦略実行＆シグナル抽出（ここはカスタム可能）
def extract_signal(result_dict):
    return {
        "signal": result_dict.get("signal", "BUY"),   # 仮に"BUY"を返す戦略とする
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
