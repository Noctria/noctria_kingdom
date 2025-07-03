# tools/structure_auditor.py

from pathlib import Path
import os
import json
from core.path_config import BASE_DIR

def audit_structure():
    issues = []

    # === 例: ディレクトリ数チェック ===
    top_level = list(BASE_DIR.glob("*"))
    if len(top_level) > 25:
        issues.append({
            "type": "too_many_directories",
            "path": ".",
            "count": len(top_level)
        })

    # === 例: 不要ファイルチェック ===
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if file.lower() in {"dammy", "dummy", "temp"}:
                issues.append({
                    "type": "unnecessary_file",
                    "path": str(Path(root) / file)
                })

    # === 保存・出力 ===
    log_path = BASE_DIR / "logs" / "structure_audit.json"
    os.makedirs(log_path.parent, exist_ok=True)
    with open(log_path, "w") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)

    print(f"✅ 構造監査完了: {log_path} に {len(issues)} 件記録")

if __name__ == "__main__":
    audit_structure()
