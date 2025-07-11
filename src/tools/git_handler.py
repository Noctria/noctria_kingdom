# src/tools/git_handler.py

import os
from subprocess import run, CalledProcessError
from core.logger import setup_logger

logger = setup_logger("GitHandler", LOGS_DIR / "tools" / "git_handler.log")

# --- 環境変数 ---
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def push_to_github(file_path: str, commit_message: str):
    """指定されたファイルをGitリポジトリに追加、コミット、プッシュする"""
    if not os.path.exists(file_path):
        logger.error(f"❌ 指定されたファイルが存在しません: {file_path}")
        return

    try:
        logger.info(f"🔄 Gitステージングを開始: {file_path}")
        run(["git", "add", file_path], check=True, capture_output=True, text=True)

        logger.info(f"💬 コミットを作成: '{commit_message}'")
        run(["git", "commit", "-m", commit_message], check=True, capture_output=True, text=True)

        logger.info("🚀 GitHubへプッシュ中...")
        if GITHUB_TOKEN:
            remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
            run(["git", "push", remote_url], check=True, capture_output=True, text=True)
        else:
            run(["git", "push"], check=True, capture_output=True, text=True)
            
        logger.info("✅ GitHubへのプッシュが完了しました。")

    except CalledProcessError as e:
        logger.error(f"❌ Git操作に失敗しました (Exit Code: {e.returncode})")
        logger.error(f"   - STDOUT: {e.stdout}")
        logger.error(f"   - STDERR: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"❌ 予期せぬエラーが発生しました: {e}", exc_info=True)
        raise
