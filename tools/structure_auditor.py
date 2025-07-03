# tools/structure_auditor.py

import os
import json
from pathlib import Path
from collections import defaultdict

from core.path_config import PROJECT_ROOT

AUDIT_LOG_PATH = PROJECT_ROOT / "logs" / "structure_audit.json"
MAX_DIR_COUNT_THRESHOLD = 25

def audit_structure():
    """Noctria Kingdom ディレクトリ構成を静的に監査"""
    results = []
    total_dir_count = 0

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dir_count = len(dirs)
        total_dir_count += dir_count

        # ディレクトリ数が多すぎる階層の警告
        if dir_count > MAX_DIR_COUNT_THRESHOLD:
            results.append({
                "type": "too_many_directories",
                "path": os.path.relpath(root, PROJECT_ROOT),
                "count": dir_count
            })

        # 不要ファイルの検出
        for file in files:
            file_path = Path(root) / file
            if file == "dammy" or file.endswith(".bak") or file.endswith("~"):
                results.append({
                    "type": "unnecessary_file",
                    "path": str(file_path.relative_to(PROJECT_ROOT))
                })

    # 保存先ディレクトリを確保
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 結果を書き出し
    with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 結果を表示
    if results:
        print("⚠️ [構造警告] 以下の項目が見つかりました：")
        for item in results:
            print(f"  - {item['type']} @ {item['path']} → {item.get('count', '')}")
    else:
        print("✅ 構造チェック完了：問題なし")

if __name__ == "__main__":
    audit_structure()
