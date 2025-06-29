import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = ["core", "veritas", "execution", "airflow_docker", "scripts"]
REPLACEMENTS = {
    # ハードコードされた文字列 : 置換後の表現（path_configの定義名）
    '"data/'              : 'str(PROCESSED_DATA_DIR / "',  # e.g., "data/xxx.csv" → str(PROCESSED_DATA_DIR / "xxx.csv")
    "'data/"              : "str(PROCESSED_DATA_DIR / '",
    '"/noctria_kingdom/'  : 'str(BASE_DIR / "',
    "'/noctria_kingdom/"  : "str(BASE_DIR / '",
    '"./data/'            : 'str(PROCESSED_DATA_DIR / "',
    "'./data/"            : "str(PROCESSED_DATA_DIR / '"
}

IMPORT_LINE = "from core.path_config import *"

def process_file(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_lines = []
    modified = False
    import_inserted = False

    for i, line in enumerate(lines):
        original_line = line
        for key, value in REPLACEMENTS.items():
            if key in line:
                line = line.replace(key, value)
                modified = True

        updated_lines.append(line)

    # 既に import 済でなければ自動挿入
    if modified and not any("from core.path_config import" in l for l in lines):
        updated_lines.insert(0, IMPORT_LINE + "\n")
        import_inserted = True

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)
        print(f"✅ Updated: {file_path.relative_to(PROJECT_ROOT)}" + (" (import added)" if import_inserted else ""))

def scan_and_replace():
    print("🔍 Scanning for hardcoded paths...")
    for dir_name in TARGET_DIRS:
        target_path = PROJECT_ROOT / dir_name
        for py_file in target_path.rglob("*.py"):
            process_file(py_file)

if __name__ == "__main__":
    scan_and_replace()
