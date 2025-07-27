from core.path_config import BASE_DIR
import subprocess
import os
from datetime import datetime

def push_generated_strategies():
    repo_dir = str(BASE_DIR)
    strategy_dir = BASE_DIR / "src" / "strategies" / "veritas_generated"  # Pathオブジェクト

    # 作業ディレクトリをリポジトリルートに変更
    os.chdir(repo_dir)

    # git add は文字列パスで指定
    subprocess.run(["git", "add", str(strategy_dir)], check=True)

    # 日本時間でのタイムスタンプ
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"🤖 Veritas戦略自動採用: {timestamp}"

    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

    print("✅ GitHubへ戦略ファイルをpushしました")
