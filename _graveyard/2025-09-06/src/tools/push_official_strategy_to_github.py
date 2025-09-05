#!/usr/bin/env python3
# coding: utf-8

"""
🤖 Veritas昇格戦略をGitHubへPushし、統治記録を残す
- 未Push戦略ファイルを `strategies/official/` から選定
- Git add → commit → push 実行
- Pushログは data/push_logs/ に JSON形式で保存
"""

import subprocess
import shutil
from datetime import datetime
import json
from pathlib import Path

from core.path_config import (
    STRATEGY_OFFICIAL_DIR,
    ACT_LOG_DIR,
    PUSH_LOG_DIR,
    GITHUB_REPO_URL  # "https://github.com/Noctria/noctria_kingdom"
)

def get_latest_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    except subprocess.CalledProcessError:
        return "unknown"

def get_github_url(strategy_path: Path) -> str:
    rel_path = strategy_path.relative_to(Path.cwd())
    return f"{GITHUB_REPO_URL}/blob/main/{rel_path.as_posix()}"

def load_act_logs() -> list:
    logs = []
    for file in Path(ACT_LOG_DIR).glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    logs.append((file, data))
        except:
            continue
    return logs

def push_to_github():
    pushed = 0
    act_logs = load_act_logs()

    for file_path, log in act_logs:
        if log.get("pushed", False):
            continue

        strategy_name = log.get("strategy")
        strategy_path = STRATEGY_OFFICIAL_DIR / strategy_name

        if not strategy_path.exists():
            print(f"⚠️ 戦略ファイルが見つかりません: {strategy_path}")
            continue

        # Git add, commit, push
        subprocess.run(["git", "add", str(strategy_path)])
        commit_message = f"🤖 Veritas戦略をofficialに自動反映（{datetime.now().date()}）"
        subprocess.run(["git", "commit", "-m", commit_message])
        subprocess.run(["git", "push"])

        # コミットハッシュとGitHub URLを取得
        commit_hash = get_latest_commit_hash()
        github_url = get_github_url(strategy_path)

        # Pushログ記録
        push_log = {
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy_name,
            "message": "Veritas戦略をGitHubへPush",
            "pushed_by": "veritas_auto",
            "commit": commit_hash,
            "github_url": github_url,
            "pushed": True
        }

        log_file_name = f"{datetime.now().isoformat().replace(':', '-')}_{strategy_name}.json"
        with open(PUSH_LOG_DIR / log_file_name, "w", encoding="utf-8") as f:
            json.dump(push_log, f, indent=2, ensure_ascii=False)

        # act_log 側も更新（pushed: true）
        log["pushed"] = True
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

        print(f"✅ {strategy_name} を GitHub にPushし、ログを記録しました")
        pushed += 1

    if pushed == 0:
        print("🔍 Push対象はありませんでした。")

if __name__ == "__main__":
    print("👑 Noctria Kingdom: GitHub Push スクリプト起動")
    push_to_github()
