import json
import importlib.util
from pathlib import Path
import pandas as pd
from core.path_config import VERITAS_ORDER_JSON, STRATEGIES_DIR

# ========================================
# ⚔️ Veritas戦略 → EA命令JSON生成スクリプト（Doフェーズ）
# ========================================

# 📌 対象戦略ファイル（固定: sample_strategy.py）
STRATEGY_PATH = STRATEGIES_DIR / "official" / "sample_strategy.py"

# 🗃 ダミー市場データを生成
def load_dummy_market_data():
    dates = pd.date_range(start="2025-01-01", periods=100, freq="h")  # ✅ 'H' → 'h'
    data = pd.DataFrame({
        "Open": 1.0,
        "High": 1.1,
        "Low": 0.9,
        "Close": 1.0,
    }, index=dates)
    return data

# 🔄 simulate関数を動的ロード
def load_simulate_function(filepath: Path):
    spec = importlib.util.spec_from_file_location("strategy_module", str(filepath))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.simulate

# 🧠 シグナル情報を抽出
def extract_signal(result_dict: dict) -> dict:
    return {
        "signal": result_dict.get("signal", "BUY"),
        "symbol": result_dict.get("symbol", "USDJPY"),
        "lot": result_dict.get("lot", 0.1),
        "tp": result_dict.get("tp", 10),
        "sl": result_dict.get("sl", 8),
    }

# ✅ Airflow対応 callable 関数
def generate_order_json():
    print("⚔️ [Veritas] EA命令生成フェーズを開始します…")

    if not STRATEGY_PATH.exists():
        print(f"❌ 戦略ファイルが存在しません: {STRATEGY_PATH}")
        return

    simulate = load_simulate_function(STRATEGY_PATH)
    market_data = load_dummy_market_data()
    result = simulate(market_data)
    signal = extract_signal(result)

    # 💾 JSON出力
    VERITAS_ORDER_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(VERITAS_ORDER_JSON, "w", encoding="utf-8") as f:
        json.dump(signal, f, indent=2)

    print("✅ EA命令ファイルを出力しました:", VERITAS_ORDER_JSON)
    print("📦 内容:", signal)
    print("📜 王国訓示:『この命、為すべき時に放たれよ。』")

# ✅ スクリプト直接実行対応
if __name__ == "__main__":
    generate_order_json()
