import os
import sys
import re
from pathlib import Path

PROJECT_ROOT = Path("/opt/airflow")
DAGS_DIR = PROJECT_ROOT / "airflow_docker" / "dags"
TARGET_EXTS = [".py"]
ENV_PATH = Path("/opt/airflow/.env")

def check_pythonpath():
    pythonpath = os.environ.get("PYTHONPATH", "")
    if "/opt/airflow" not in pythonpath:
        print("❌ PYTHONPATH に '/opt/airflow' が含まれていません")
    else:
        print("✅ PYTHONPATH 設定 OK:", pythonpath)

def check_required_paths():
    required_paths = [
        PROJECT_ROOT / "core" / "path_config.py",
        PROJECT_ROOT / "core" / "risk_management.py",
        PROJECT_ROOT / "core" / "risk_control.py",
        PROJECT_ROOT / "strategies" / "Aurus_Singularis.py",
        PROJECT_ROOT / "strategies" / "aurus_singularis.py",
    ]
    for path in required_paths:
        if not path.exists():
            print(f"❌ ファイルが見つかりません: {path}")
        else:
            print(f"✅ 存在確認 OK: {path}")

def extract_imports_from_file(file_path):
    imports = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if line.strip().startswith("from ") or line.strip().startswith("import "):
                imports.append((i + 1, line.strip()))
    return imports

def check_dag_imports():
    print("\n📦 DAG内のインポート文チェック:")
    for file in DAGS_DIR.glob("*.py"):
        imports = extract_imports_from_file(file)
        print(f"\n🗂️ {file.name}")
        for lineno, imp in imports:
            print(f"  L{lineno}: {imp}")

def main():
    print("🔍 Noctria Kingdom インポートパスチェック")
    print("==========================================")
    check_pythonpath()
    check_required_paths()
    check_dag_imports()

if __name__ == "__main__":
    main()
