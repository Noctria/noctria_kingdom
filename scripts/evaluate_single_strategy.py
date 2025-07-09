#!/usr/bin/env python3
# coding: utf-8

"""
📄 evaluate_single_strategy.py
- 単一戦略ファイルを指定して評価を実行
- 採用基準に基づいて official に昇格
- 結果は logs/veritas_eval_result.json に追記
"""

import sys
import os
import json
from datetime import datetime
from core.path_config import STRATEGIES_DIR, LOGS_DIR, DATA_DIR
from core.market_loader import load_market_data
from core.strategy_evaluator import evaluate_strategy, is_strategy_adopted

def main():
    if len(sys.argv) < 2:
        print("❌ 戦略ファイル名（例: veritas_strategy_20250710_0900.py）を引数に指定してください")
        sys.exit(1)

    strategy_name = sys.argv[1]
    strategy_path = STRATEGIES_DIR / "veritas_generated" / strategy_name

    if not strategy_path.exists():
        print(f"❌ 戦略ファイルが存在しません: {strategy_path}")
        sys.exit(1)

    market_data_path = DATA_DIR / "market_data.csv"
    official_dir = STRATEGIES_DIR / "official"
    log_path = LOGS_DIR / "veritas_eval_result.json"

    os.makedirs(official_dir, exist_ok=True)
    os.makedirs(log_path.parent, exist_ok=True)

    market_data = load_market_data(str(market_data_path))
    result = evaluate_strategy(str(strategy_path), market_data)

    if is_strategy_adopted(result):
        save_path = official_dir / strategy_name
        with open(strategy_path, "r") as src, open(save_path, "w") as dst:
            dst.write(src.read())
        print(f"✅ 採用: {strategy_name}（資産 {result['final_capital']:,.0f}円）")
        result["status"] = "adopted"
    elif result["status"] == "ok":
        print(f"❌ 不採用: {strategy_name}")
        result["status"] = "rejected"
    else:
        print(f"🚫 エラー: {strategy_name} ➜ {result.get('error_message')}")
        result["status"] = "error"

    # ✅ ログ追記
    if log_path.exists():
        with open(log_path, "r") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(result)
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=2)

if __name__ == "__main__":
    main()
