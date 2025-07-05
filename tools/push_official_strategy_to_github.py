import os
import subprocess
from datetime import datetime

# プロジェクトルートを自動検出
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OFFICIAL_DIR = os.path.join(REPO_ROOT, "strategies", "official")

def run(cmd):
    """コマンド実行ユーティリティ"""
    print(f"💻 {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("✅")
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")

def git_push_official_strategies():
    os.chdir(REPO_ROOT)

    # git branch 判定
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
    except subprocess.CalledProcessError:
        print("❌ Gitブランチを取得できませんでした")
        return

    # 対象ディレクトリがなければ作成
    if not os.path.exists(OFFICIAL_DIR):
        print(f"📁 strategies/official/ が存在しないため作成します")
        os.makedirs(OFFICIAL_DIR, exist_ok=True)
        with open(os.path.join(OFFICIAL_DIR, ".gitkeep"), "w") as f:
            f.write("")

    # .py ファイルの一覧
    new_files = []
    for file in os.listdir(OFFICIAL_DIR):
        if file.endswith(".py"):
            rel_path = os.path.join("strategies", "official", file)
            result = subprocess.run(["git", "ls-files", "--error-unmatch", rel_path],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode != 0:
                new_files.append(rel_path)

    if not new_files:
        print("✅ 新たにpushすべき戦略ファイルはありません")
        return

    print(f"📦 新規push対象: {new_files}")
    for path in new_files:
        run(["git", "add", path])

    commit_message = f"🤖 Veritas戦略をofficialに自動反映（{datetime.utcnow().date()}）"
    run(["git", "commit", "-m", commit_message])
    run(["git", "push", "origin", branch])
    print("🚀 GitHubにpush完了")

if __name__ == "__main__":
    git_push_official_strategies()
