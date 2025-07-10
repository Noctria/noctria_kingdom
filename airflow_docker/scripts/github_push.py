# airflow_docker/scripts/github_push.py

import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# ✅ プロジェクトルートの .env をロード
project_root = Path(__file__).resolve().parents[1]
dotenv_path = project_root / ".env"

if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"⚠️ .envファイルが見つかりません（継続）: {dotenv_path}")

def run_command(cmd: list[str]):
    print(f"💻 {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ Error: {result.stderr.strip()}")
    else:
        print(f"✅ {result.stdout.strip()}")
    return result.returncode

def main():
    # 🧠 Git user 情報のセット
    commands = [
        ["git", "config", "--global", "user.email", "veritas@noctria.ai"],
        ["git", "config", "--global", "user.name", "Veritas Machina"],
        ["git", "add", "strategies/veritas_generated/"],
        ["git", "commit", "-m", "🤖 Veritas採用戦略を自動コミット"],
        ["git", "push", "origin", "main"]
    ]

    for cmd in commands:
        code = run_command(cmd)
        if code != 0:
            # ⚠️ 変更がなく commit 失敗するのは正常（commitはスキップして終了）
            if "commit" in cmd:
                print("ℹ️ 変更なしのため、commitはスキップされました")
            break

if __name__ == "__main__":
    main()
