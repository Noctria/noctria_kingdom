# airflow_docker/scripts/github_push.py

import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# ✅ プロジェクトルートの .env をロード
project_root = Path(__file__).resolve().parents[1]
dotenv_path = project_root / ".env"

if not dotenv_path.exists():
    raise FileNotFoundError(f"❌ .envファイルが見つかりません: {dotenv_path}")

load_dotenv(dotenv_path=dotenv_path)

def run_command(cmd: list[str]):
    print(f"💻 {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ Error: {result.stderr.strip()}")
    else:
        print(f"✅ {result.stdout.strip()}")
    return result.returncode

def main():
    # GITHUB_PATの使用は不要（初回 clone で認証済のため）
    commands = [
        ["git", "config", "--global", "user.email", "veritas@noctria.ai"],
        ["git", "config", "--global", "user.name", "Veritas Machina"],
        ["git", "add", "strategies/official/"],
        ["git", "commit", "-m", "🤖 Veritas戦略をofficialに自動反映"],
        ["git", "push", "origin", "main"]
    ]

    for cmd in commands:
        code = run_command(cmd)
        if code != 0:
            if "commit" in cmd:
                print("ℹ️ 変更なしのため、commitはスキップされました")
            break

if __name__ == "__main__":
    main()
