# scripts/github_push.py

import os
import subprocess
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OFFICIAL_DIR = os.path.join(REPO_ROOT, "strategies", "official")

def git_push_official_strategies():
    os.chdir(REPO_ROOT)

    # git branch 判定（main or master）
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
    except subprocess.CalledProcessError:
        print("❌ Gitブランチを取得できませんでした")
        return

    # 追加対象の .py ファイル一覧
    new_files = []
    for file in os.listdir(OFFICIAL_DIR):
        if file.endswith(".py"):
            full_path = os.path.join("strategies", "official", file)
            # git 管理下にないファイル、または変更済み
            result = subprocess.run(["git", "ls-files", "--error-unmatch", full_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode != 0:
                new_files.append(full_path)

    if not new_files:
        print("✅ 新たにpushすべき戦略ファイルはありません")
        return

    print(f"📦 新規push対象: {new_files}")
    for path in new_files:
        subprocess.run(["git", "add", path])

    commit_message = f"✅ Adopted strategies by Veritas on {datetime.utcnow().date()}"
    subprocess.run(["git", "commit", "-m", commit_message])
    subprocess.run(["git", "push", "origin", branch])
    print("🚀 GitHubにpush完了")

if __name__ == "__main__":
    git_push_official_strategies()
