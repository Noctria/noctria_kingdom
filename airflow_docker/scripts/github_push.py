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

def run_command(cmd: list[str], allow_fail: bool = False):
    """Shellコマンドを実行し、標準出力・エラーを表示"""
    print(f"\n💻 {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Error:\n{result.stderr.strip()}")
        if not allow_fail:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    else:
        if result.stdout.strip():
            print(f"✅ {result.stdout.strip()}")

    return result

def main():
    print("🚀 Veritas採用戦略をGitHubに自動Push開始")

    # ✅ Git user config（Airflow環境などでは省略可）
    run_command(["git", "config", "--global", "user.email", "veritas@noctria.ai"], allow_fail=True)
    run_command(["git", "config", "--global", "user.name", "Veritas Machina"], allow_fail=True)

    # ✅ ステータス確認（デバッグ用）
    run_command(["git", "status"])

    # ✅ add & commit & push
    run_command(["git", "add", "strategies/veritas_generated/"])

    commit_result = run_command(["git", "commit", "-m", "🤖 Veritas採用戦略を自動コミット"], allow_fail=True)
    if "nothing to commit" in commit_result.stderr.lower():
        print("ℹ️ 変更なしのため、commitはスキップされました")
        return

    run_command(["git", "push", "origin", "main"])

    print("✅ GitHubへのPushが完了しました")

if __name__ == "__main__":
    main()
