#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas戦略の昇格戦略を GitHub に公式Pushするスクリプト
- 対象戦略は strategies/official/ 内のファイル
- commit & push 成功時に push_logs に記録を残す
"""

import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

# ✅ 王国の地図（標準パス管理）
from core.path_config import STRATEGIES_DIR, DATA_DIR

# ========================================
# 📌 設定
# ========================================
OFFICIAL_DIR = STRATEGIES_DIR / "official"
PUSH_LOG_PATH = DATA_DIR / "push_logs" / "push_history.json"

# ========================================
# 🔧 シェルコマンド実行
# ========================================
def run(cmd: list[str]):
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        raise

# ========================================
# 💾 Pushログ保存（追記）
# ========================================
def save_push_log(strategy_name: str, commit_message: str):
    PUSH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "strategy": strategy_name,
        "commit_message": commit_message,
        "author": os.getenv("GIT_AUTHOR_NAME", "Veritas Bot"),
        "pushed": True
    }
    if PUSH_LOG_PATH.exists():
        with open(PUSH_LOG_PATH, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(log_entry)
    with open(PUSH_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

    print(f"📜 Pushログを記録しました: {PUSH_LOG_PATH}")

# ========================================
# 🚀 Push実行（add → commit → push）
# ========================================
def push_strategy(strategy_filename: str):
    os.chdir(STRATEGIES_DIR.parent)  # プロジェクトルートへ移動
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
    rel_path = f"strategies/official/{strategy_filename}"

    # Git add → commit → push
    run(["git", "add", rel_path])
    commit_msg = f"🧠 Veritas戦略 '{strategy_filename}' を昇格しPush"
    run(["git", "commit", "-m", commit_msg])
    run(["git", "push", "origin", branch])

    # ✅ Pushログに記録
    save_push_log(strategy_filename, commit_msg)

    print(f"✅ 戦略 '{strategy_filename}' をGitHubへ昇格Pushしました")

# ========================================
# 🏁 CLI実行
# ========================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy", help="Push対象の戦略ファイル名（例: sample_strategy.py）")
    args = parser.parse_args()

    push_strategy(args.strategy)
