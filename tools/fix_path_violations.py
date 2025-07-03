from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = ["veritas", "scripts", "execution", "airflow_docker", "tests"]

# sys.path.append 系（Airflowやローカル構築用）
SYS_PATH_PATTERN = re.compile(r"^\s*sys\.path\.append\(.*\)\s*(#.*)?$")

# ハードコードされた出力パスの置換パターン
FIXED_PATH_REPLACEMENTS = {
    r'["\']/mnt/[a-z]/noctria-kingdom-main/strategies/veritas_generated["\']':
        'str(GENERATED_STRATEGIES_DIR)',
    r'["\']/mnt/[a-z]/noctria-kingdom-main/airflow_docker/models/[^"\']+["\']':
        'str(MODELS_DIR)',  # 概ね合致させる（調整可）
    r'["\']/mnt/[a-z]/noctria-kingdom-main["\']':
        'str(BASE_DIR)',
    r'"data/([^\"]+)"':
        r'str(PROCESSED_DATA_DIR / "\1")',
    r"'data/([^']+)'":
        r"str(PROCESSED_DATA_DIR / '\1')",
}

IMPORT_LINE = "from core.path_config import *"

def process_file(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    modified = False
    new_lines = []
    for line in lines:
        # sys.path.append の削除
        if SYS_PATH_PATTERN.match(line):
            print(f"🗑️  Removed sys.path.append in {file_path.name}")
            modified = True
            continue

        # 固定パスの置換
        original_line = line
        for pattern, replacement in FIXED_PATH_REPLACEMENTS.items():
            line = re.sub(pattern, replacement, line)
        if line != original_line:
            modified = True
        new_lines.append(line)

    if modified:
        # import path_config が含まれていなければ追加
        if not any("from core.path_config import" in l for l in new_lines):
            new_lines.insert(0, IMPORT_LINE + "\n")
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"✅ Updated: {file_path.relative_to(PROJECT_ROOT)}")

def apply_fixes():
    print("🛠️ Fixing hardcoded path violations...")
    for target_dir in TARGET_DIRS:
        for file in (PROJECT_ROOT / target_dir).rglob("*.py"):
            process_file(file)

if __name__ == "__main__":
    apply_fixes()