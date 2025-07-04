# scripts/push_generated_strategy.py
import subprocess
import os
from datetime import datetime

def push_generated_strategies():
    repo_dir = "/mnt/e/noctria-kingdom-main"
    strategy_dir = "strategies/veritas_generated"

    os.chdir(repo_dir)

    subprocess.run(["git", "add", strategy_dir], check=True)

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"🤖 Veritas戦略自動採用: {timestamp}"
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

    print("✅ GitHubへ戦略ファイルをpushしました")
