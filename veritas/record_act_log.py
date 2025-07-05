#!/usr/bin/env python3
# coding: utf-8

import json
from datetime import datetime
from pathlib import Path
from core.path_config import VERITAS_EVAL_LOG, STRATEGIES_DIR, DATA_DIR

# 📁 保存先ディレクトリ
ACT_LOG_DIR = DATA_DIR / "act_logs"
ACT_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ✅ 評価ログの読み込み
def load_latest_eval():
    if not VERITAS_EVAL_LOG.exists():
        print(f"❌ 評価ログが存在しません: {VERITAS_EVAL_LOG}")
        return None

    with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
        return json.load(f)

# ✅ 採用戦略ログを保存
def save_adopted_log(entry: dict):
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    out_path = ACT_LOG_DIR / f"{timestamp}.json"

    # pushed フラグを明示
    entry["timestamp"] = timestamp
    entry["pushed"] = False

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)

    print(f"📜 採用戦略ログを記録しました: {out_path}")

def main():
    print("📝 [Veritas] 採用戦略ログ記録フェーズを開始…")

    eval_data = load_latest_eval()
    if not eval_data:
        return

    adopted = eval_data.get("adopted", [])
    if not adopted:
        print("📭 採用された戦略がありません")
        return

    for entry in adopted:
        save_adopted_log(entry)

    print("👑 採用戦略の記録を完了しました")

if __name__ == "__main__":
    main()
