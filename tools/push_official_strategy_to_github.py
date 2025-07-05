#!/usr/bin/env python3
# coding: utf-8

import os
import subprocess
from datetime import datetime
from pathlib import Path
import json

# ========================================
# 📌 Noctria Kingdom - GitHub Push Script
#   - Veritas戦略を official に移送し、署名付きでGitHubへ反映
# ========================================

# ✅ プロジェクトルート
REPO_ROOT = Path(__file__).resolve().parent.parent
OFFICIAL_DIR = REPO_ROOT / "strategies" / "official"
SOURCE_DIR = REPO_ROOT / "strategies" / "veritas_generated"
PUSH_LOG_DIR = REPO_ROOT / "data" / "push_logs"
PUSH_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ✅ Gitコマンド実行ユーティリティ
def run(cmd):
    print(f"💻 {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("✅")
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")

# ✅ コミットハッシュ取得
def get_current_commit_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    except subprocess.CalledProcessError:
        return "unknown"

# ✅ 署名コメントを挿入（既にある場合はスキップ）
def insert_signature_comment(filepath: Path, source_path: Path, commit_hash: str):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "# 📝 Veritas Push Info:" in content:
        print(f"🔹 既に署名済み: {filepath.name}")
        return

    signature = f'''# 📝 Veritas Push Info:
# - Date: {datetime.utcnow().date()}
# - Commit: {commit_hash}
# - Source: {source_path.relative_to(REPO_ROOT)}'''

    new_content = signature + "\n\n" + content

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✍️ 署名を追加しました: {filepath.name}")

# ✅ Pushログを保存
def record_push_log(strategy_name: str, source_path: Path, commit_hash: str):
    log_data = {
        "strategy": strategy_name,
        "pushed_at": datetime.utcnow().isoformat(),
        "commit": commit_hash,
        "source": str(source_path.relative_to(REPO_ROOT))
    }
    filename = f"{strategy_name.replace('.py', '')}_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
    with open(PUSH_LOG_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    print(f"📜 Pushログを保存しました: {filename}")

# ✅ メイン処理
def git_push_official_strategies():
    os.chdir(REPO_ROOT)

    commit_hash = get_current_commit_hash()

    # コピー対象の戦略一覧
    new_files = []
    for file in os.listdir(SOURCE_DIR):
        if file.endswith(".py"):
            src_path = SOURCE_DIR / file
            dst_path = OFFICIAL_DIR / file

            # コピー
            content = src_path.read_text(encoding="utf-8")
            dst_path.write_text(content, encoding="utf-8")

            # 署名挿入
            insert_signature_comment(dst_path, src_path, commit_hash)

            new_files.append(dst_path)

            # Pushログ
            record_push_log(file, src_path, commit_hash)

    if not new_files:
        print("✅ 新たにpushすべき戦略ファイルはありません")
        return

    # Git add/commit/push
    for path in new_files:
        rel_path = str(path.relative_to(REPO_ROOT))
        run(["git", "add", rel_path])

    commit_msg = f"🤖 Veritas戦略をofficialに署名付きで反映（{datetime.utcnow().date()}）"
    run(["git", "commit", "-m", commit_msg])
    run(["git", "push"])

    print("🚀 GitHubへのPush完了")

if __name__ == "__main__":
    git_push_official_strategies()
