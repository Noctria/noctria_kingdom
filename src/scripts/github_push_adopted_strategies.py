#!/usr/bin/env python3
# coding: utf-8

import os
import json
from datetime import datetime
from pathlib import Path
import subprocess

from core.path_config import (
    REPO_ROOT,
    STRATEGIES_DIR,
    GITHUB_PUSH_SCRIPT,
    ACT_LOG_DIR,  # = /data/act_logs/
)

OFFICIAL_DIR = STRATEGIES_DIR / "official"

def run(cmd):
    """Gitコマンド実行"""
    print(f"💻 {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("✅")
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")

def git_push_file(filepath: Path):
    os.chdir(REPO_ROOT)
    rel_path = filepath.relative_to(REPO_ROOT)

    run(["git", "add", str(rel_path)])
    commit_message = f"👑 昇格戦略をofficialに反映: {filepath.name}（{datetime.utcnow().date()}）"
    run(["git", "commit", "-m", commit_message])
    run(["git", "push", "origin", "main"])

def push_unpushed_adopted_strategies():
    print("🚀 昇格戦略ログを確認中…")
    logs = sorted(ACT_LOG_DIR.glob("*.json"))

    for log_file in logs:
        with open(log_file, "r", encoding="utf-8") as f:
            log_data = json.load(f)

        if log_data.get("pushed", False):
            continue

        strategy_name = log_data.get("strategy")
        strategy_path = OFFICIAL_DIR / strategy_name

        if not strategy_path.exists():
            print(f"❌ 対象戦略ファイルが存在しません: {strategy_path}")
            continue

        # 🔁 GitHubへ反映
        git_push_file(strategy_path)

        # 🔄 pushedフラグをTrueに更新
        log_data["pushed"] = True
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        print(f"📜 GitHubに反映完了 & ログ更新: {log_file.name}")

if __name__ == "__main__":
    push_unpushed_adopted_strategies()
