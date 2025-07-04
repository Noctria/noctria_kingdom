import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = ["core", "veritas", "execution", "airflow_docker", "scripts", "tests"]
PATTERNS = [
    r'["\']data/',                        # "data/" or 'data/'
    r'["\']\.\/data/',                    # "./data/" (相対)
    r'["\']/noctria_kingdom/',            # 絶対ハードコード
    r'["\']/mnt/[a-z]/noctria-kingdom',   # WSLパス
    r'sys\.path\.append\(',               # sys.path.append 使用の直接操作
    r'\.\./',                             # 上位ディレクトリ参照
]

EXCLUDE_FILES = ["core/path_config.py"]

def scan_file(file_path: Path):
    violations = []
    if any(str(file_path).endswith(exclude) for exclude in EXCLUDE_FILES):
        return violations

    with open(file_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            for pattern in PATTERNS:
                if re.search(pattern, line):
                    violations.append((lineno, line.strip()))
                    break
    return violations

def scan_project():
    total_issues = 0
    print("🔍 Scanning for hardcoded paths NOT using `path_config.py`...\n")

    for target_dir in TARGET_DIRS:
        path = PROJECT_ROOT / target_dir
        for py_file in path.rglob("*.py"):
            violations = scan_file(py_file)
            if violations:
                print(f"🚫 Found in: {py_file.relative_to(PROJECT_ROOT)}")
                for lineno, code in violations:
                    print(f"  [L{lineno:3}] {code}")
                print()
                total_issues += len(violations)

    if total_issues == 0:
        print("✅ All clean. No hardcoded paths found.")
    else:
        print(f"⚠️ Total issues detected: {total_issues}")

if __name__ == "__main__":
    scan_project()
