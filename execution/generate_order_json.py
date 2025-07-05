import json
import importlib.util
from pathlib import Path
from datetime import datetime
import pandas as pd

# ========================================
# ⚔️ Veritas戦略 → EA命令JSON生成スクリプト（Doフェーズ）
# ========================================

# ✅ Noctria Kingdom 標準パス管理
from core.path_config import (
    STRATEGIES_DIR,
    VERITAS_ORDER_JSON,
    PDCA_LOG_DIR,
)

# 📌 実行対象戦略（今後は自動選定に拡張可）
TARGET_STRATEGY = "sample_strategy.py"
STRATEGY_PATH = STRATEGIES_DIR / "official" / TARGET_STRATEGY

# 🗃 ダミー市場データ（H→hで警告回避）
def load_dummy_market_data():
    dates = pd.date_range(start="2025-01-01", periods=100, freq="h")
    data = pd.DataFrame({
        "Open": 1.0,
        "High": 1.1,
        "Low": 0.9,
        "Close": 1.0,
    }, index=dates)
    return data

# 🔄 simulate関数をロード
def load_simulate_function(filepath: Path):
    spec = importlib.util.spec_from_file_location("strategy_module", str(filepath))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.simulate

# 🧠 シグナル抽出
def extract_signal(result_dict: dict) -> dict:
    return {
        "strategy": TARGET_STRATEGY,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "signal": result_dict.get("signal", "BUY"),
        "symbol": result_dict.get("symbol", "USDJPY"),
        "lot": result_dict.get("lot", 0.1),
        "tp": result_dict.get("tp", 10),
        "sl": result_dict.get("sl", 8),
    }

# 💾 PDCA履歴ログ保存
def save_pdca_log(signal_dict: dict):
    PDCA_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = signal_dict["timestamp"].replace(":", "-")
    out_path = PDCA_LOG_DIR / f"{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(signal_dict, f, indent=2, ensure_ascii=False)
    print(f"🗂️ PDCA履歴ログを保存しました: {out_path}")

# ✅ メイン関数（Airflow & CLI 両対応）
def generate_order_json():
    print("⚔️ [Veritas] EA命令生成フェーズを開始します…")

    if not STRATEGY_PATH.exists():
        print(f"❌ 戦略ファイルが見つかりません: {STRATEGY_PATH}")
        return

    simulate = load_simulate_function(STRATEGY_PATH)
    market_data = load_dummy_market_data()
    result = simulate(market_data)
    signal = extract_signal(result)

    # 📤 EA命令ファイル出力
    VERITAS_ORDER_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(VERITAS_ORDER_JSON, "w", encoding="utf-8") as f:
        json.dump(signal, f, indent=2, ensure_ascii=False)

    print("✅ EA命令ファイルを出力しました:", VERITAS_ORDER_JSON)
    print("📦 内容:", signal)

    # 🧾 履歴ログとして保存
    save_pdca_log(signal)

    print("📜 王国訓示:『この命、記されし記録として未来に残らん。』")

# ✅ 手動実行対応
if __name__ == "__main__":
    generate_order_json()
