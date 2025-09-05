#!/usr/bin/env python3
# coding: utf-8

"""
Veritas戦略自動保存 + GitHub自動Pushスクリプト
👑 by Noctria Kingdom
"""

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# .env読み込み
load_dotenv()

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "Noctria")
GITHUB_REPO = os.getenv("GITHUB_REPO", "noctria_kingdom")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def save_and_push_strategy(code: str, strategy_name: str = None):
    """
    Veritasが生成したコードを .py に保存し、GitHubに自動Pushする。
    
    Parameters:
        code (str): 生成された戦略コード（Python形式）
        strategy_name (str): 任意のファイル名（デフォルト: 日時付き）
    """

    now = datetime.now().strftime("%Y%m%d_%H%M")
    filename = strategy_name or f"strategy_{now}.py"
    save_dir = "/opt/airflow/strategies/veritas_generated"
    save_path = os.path.join(save_dir, filename)

    # 📁 ディレクトリが無ければ作成
    os.makedirs(save_dir, exist_ok=True)

    # 💾 ファイル保存
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"💾 Veritas戦略を保存しました: {save_path}")

    # ✅ Gitユーザー設定（省略可：一度設定済みなら不要）
    subprocess.run(["git", "config", "--global", "user.name", GITHUB_USERNAME], check=True)
    subprocess.run(["git", "config", "--global", "user.email", f"{GITHUB_USERNAME}@users.noreply.github.com"], check=True)

    # ✅ Git add → commit → push
    try:
        subprocess.run(["git", "add", save_path], check=True)
        subprocess.run(["git", "commit", "-m", f"🤖 Veritas戦略自動追加: {filename}"], check=True)

        # トークン付きURLでpush（環境変数がある場合のみ）
        if GITHUB_TOKEN:
            remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
            subprocess.run(["git", "push", remote_url], check=True)
        else:
            subprocess.run(["git", "push"], check=True)

        print("🚀 GitHubに自動Push完了しました！")

    except subprocess.CalledProcessError as e:
        print(f"❌ Git操作でエラーが発生しました: {e}")
