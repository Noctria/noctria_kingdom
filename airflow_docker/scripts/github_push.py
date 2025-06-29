# airflow_docker/scripts/github_push.py

import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# ✅ .envファイルの自動解決（プロジェクトルート想定）
project_root = Path(__file__).resolve().parents[1]
dotenv_path = project_root / ".env"

if not dotenv_path.exists():
    raise FileNotFoundError(f"❌ .envファイルが見つかりません: {dotenv_path}")

load_dotenv(dotenv_path=dotenv_path)

def run_command(cmd: list[str]) -> int:
    print(f"💻 {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ Error: {result.stderr.strip()}")
    else:
        print(f"✅ {result.stdout.strip()}")
    return result.returncode

def has_staged_changes() -> bool:
    """ステージされた差分があるかを確認"""
    return subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0

def main():
    token = os.getenv("GITHUB_PAT")
    if not token:
        raise ValueError("❌ GITHUB_PATが環境変数に設定されていません（.envを確認）")

    repo_url = f"https://Noctria:{token}@github.com/Noctria/noctria_kingdom.git"

    # 初期設定とadd
    initial_commands = [
        ["git", "config", "--global", "user.email", "veritas@noctria.ai"],
        ["git", "config", "--global", "user.name", "Veritas Machina"],
        ["git", "add", "strategies/official/"],
    ]
    for cmd in initial_commands:
        if run_command(cmd) != 0:
            return

    # コミット（差分があるときのみ）
    if has_staged_changes():
        run_command(["git", "commit", "-m", "🤖 Veritas戦略をofficialに自動反映"])
    else:
        print("ℹ️ 変更なしのため、commitはスキップされました")

    # Push処理
    push_commands = [
        ["git", "remote", "set-url", "origin", repo_url],
        ["git", "push", "origin", "main"]
    ]
    for cmd in push_commands:
        run_command(cmd)

if __name__ == "__main__":
    main()
