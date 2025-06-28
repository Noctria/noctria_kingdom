import os
import json
from pathlib import Path

# 設定
ROOT_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT_DIR / "logs"
LOG_FILE = LOGS_DIR / "structure_audit.json"

# 問題判定ルール
IGNORED_DIRS = {".git", ".venv", "__pycache__", "logs", "tmp", ".mypy_cache", ".idea"}
SHOULD_NOT_EXIST = {"dammy", "dummyfile"}
TOO_MANY_FILES_THRESHOLD = 50
TOO_MANY_DIRS_THRESHOLD = 20

def scan_directory(base_path: Path):
    issues = []
    for root, dirs, files in os.walk(base_path):
        rel_root = Path(root).relative_to(base_path)

        # 無視ディレクトリをスキップ
        if any(part in IGNORED_DIRS for part in rel_root.parts):
            continue

        # 不要ディレクトリの検出
        for d in dirs:
            if d in SHOULD_NOT_EXIST:
                issues.append({
                    "type": "unnecessary_directory",
                    "path": str(rel_root / d)
                })

        # 不要ファイルの検出
        for f in files:
            if f in SHOULD_NOT_EXIST:
                issues.append({
                    "type": "unnecessary_file",
                    "path": str(rel_root / f)
                })

        # 過剰ファイル数の警告
        if len(files) > TOO_MANY_FILES_THRESHOLD:
            issues.append({
                "type": "too_many_files",
                "path": str(rel_root),
                "count": len(files)
            })

        # 過剰ディレクトリ数の警告
        if len(dirs) > TOO_MANY_DIRS_THRESHOLD:
            issues.append({
                "type": "too_many_directories",
                "path": str(rel_root),
                "count": len(dirs)
            })

    return issues

def main():
    print(f"🔍 Scanning: {ROOT_DIR}")
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    issues = scan_directory(ROOT_DIR)

    with LOG_FILE.open("w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)

    print(f"✅ Audit complete. Issues found: {len(issues)}")
    print(f"📄 Log saved to: {LOG_FILE}")

if __name__ == "__main__":
    main()
