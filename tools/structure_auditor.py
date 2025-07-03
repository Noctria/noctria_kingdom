# tools/structure_refactor.py

import sys
import os
from pathlib import Path

# === パス設定 ===
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parent.parent
sys.path.append(str(ROOT_DIR))  # ← これが大事！！！

from tools.hardcoded_path_replacer import replace_paths
from tools.structure_auditor import main as audit_main

# === 各種対象ディレクトリ ===
TARGETS = [
    ROOT_DIR / "airflow_docker" / "dags",
    ROOT_DIR / "airflow_docker" / "plugins",
    ROOT_DIR / "airflow_docker" / "scripts",
    ROOT_DIR / "core",
    ROOT_DIR / "strategies",
    ROOT_DIR / "veritas",
    ROOT_DIR / "tools",
]

def refactor_all():
    print(f"🚀 Root: {ROOT_DIR}")
    for target in TARGETS:
        if target.exists():
            print(f"🔧 Replacing paths in: {target}")
            for root, _, files in os.walk(target):
                for file in files:
                    if file.endswith(".py"):
                        path = Path(root) / file
                        try:
                            replace_paths(path)
                        except Exception as e:
                            print(f"❌ Error processing {path}: {e}")
        else:
            print(f"⚠️ Not found: {target}")

    print("✅ Replacements complete. Running structure audit...")
    audit_main()

if __name__ == "__main__":
    refactor_all()
