# tools/generate_cleanup_script.py

import json
from pathlib import Path

# パス設定
BASE_DIR = Path(__file__).resolve().parent.parent
AUDIT_LOG_PATH = BASE_DIR / "logs" / "structure_audit.json"
OUTPUT_SCRIPT = BASE_DIR / "tools" / "cleanup_commands.sh"

def generate_cleanup_commands():
    if not AUDIT_LOG_PATH.exists():
        print(f"❌ 構造監査ログが見つかりません: {AUDIT_LOG_PATH}")
        return

    with open(AUDIT_LOG_PATH, "r") as f:
        issues = json.load(f)

    cmds = ["#!/bin/bash\n", "echo '🚨 クリーンアップ開始'\n"]

    for issue in issues:
        t = issue["type"]
        if t in {"unnecessary_file", "python_cache_file", "backup_file"}:
            path = issue["path"]
            cmds.append(f"rm -f '{path}'  # {t}\n")

        elif t == "double_nested_airflow":
            path = issue["path"]
            cmds.append(f"rm -rf '{path}'  # 不正な二重ネスト構造\n")

        elif t == "duplicate_filename":
            # 原則として1つを残し、他は削除（要レビュー）
            paths = issue["paths"]
            keep = paths[0]
            for path in paths[1:]:
                cmds.append(f"# ⚠️ 重複: '{issue['name']}' → 一方を残す\n")
                cmds.append(f"rm -f '{path}'  # duplicate_filename\n")

        elif t == "duplicate_directory_case":
            # 名前が異なるだけで内容が重複していそうなディレクトリ
            paths = issue["paths"]
            cmds.append(f"# ⚠️ 大文字小文字の混在 → 手動で統一検討\n")
            for p in paths:
                cmds.append(f"# ls '{p}'\n")

        elif t == "too_many_directories":
            cmds.append("# ⚠️ トップレベルのディレクトリが多すぎます（整理推奨）\n")

        else:
            cmds.append(f"# ⚠️ 未対応の種類: {t}\n")

    cmds.append("\necho '✅ クリーンアップスクリプト生成完了'\n")

    # 保存
    with open(OUTPUT_SCRIPT, "w") as f:
        f.writelines(cmds)

    print(f"✅ 自動生成完了: {OUTPUT_SCRIPT}")

if __name__ == "__main__":
    generate_cleanup_commands()
