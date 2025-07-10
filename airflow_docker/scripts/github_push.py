#!/usr/bin/env python3
# coding: utf-8

"""
🤖 Veritas採用戦略をGitHubに自動Pushするスクリプト
- Airflow DAGから呼び出されることを前提
- .envからGitHub設定を読み取り
"""

import os
import subprocess
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# ================================
# 📌 プロジェクトルート & .env ロード
# ================================
project_root = Path(__file__).resolve().parents[1]
dotenv_path = project_root / ".env"

if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    print(f"✅ .env読み込み成功: {dotenv_path}")
else:
    print(f"⚠️ .envファイルが見つかりません（継続）: {dotenv_path}")

# ================================
# 🛠️ コマンド実行ユーティリティ
# ================================
def run_command(cmd: List[str], allow_fail: bool = False) -> subprocess.CompletedProcess:
    """Shellコマンドを実行し、標準出力・エラーを表示"""
    print(f"\n💻 実行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ エラー:\n{result.stderr.strip()}")
        if not allow_fail:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    else:
        if result.stdout.strip():
            print(f"✅ 出力:\n{result.stdout.strip()}")

    return result

# ================================
# 🚀 メイン処理
# ================================
def main():
    print("🚀 Veritas採用戦略をGitHubに自動Push開始")

    # ✅ Git config（CI環境では必要）
    run_command(["git", "config", "--global", "user.email", "veritas@noctria.ai"], allow_fail=True)
    run_command(["git", "config", "--global", "user.name", "Veritas Machina"], allow_fail=True)

    # ✅ ステータス確認（デバッグ用）
    run_command(["git", "status"], allow_fail=True)

    # ✅ ステージング（戦略ファイル群）
    run_command(["git", "add", "strategies/veritas_generated/"])

    # ✅ コミット（変更がない場合はスキップ）
    commit_result = run_command(
        ["git", "commit", "-m", "🤖 Veritas採用戦略を自動コミット"],
        allow_fail=True
    )

    output = (commit_result.stdout or "") + (commit_result.stderr or "")
    if "nothing to commit" in output.lower():
        print("ℹ️ 変更なしのため、commitはスキップされました")
        return

    # ✅ Push
    run_command(["git", "push", "origin", "main"])

    print("✅ GitHubへのPushが完了しました")

# ================================
# 🔧 Airflowなどから呼び出し可能
# ================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ GitHub Push失敗: {e}")
        exit(1)
