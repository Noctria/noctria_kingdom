from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
# tools/structure_refactor.py

from pathlib import Path
import os
import sys

# 🔧 パスを通す（/mnt/d/noctria_kingdom を PYTHONPATH に追加する想定）
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parent.parent
sys.path.append(str(ROOT_DIR))

# === 各種モジュールインポート ===
from core.path_config import (
    DAGS_DIR, PLUGINS_DIR, SCRIPTS_DIR, CORE_DIR, STRATEGIES_DIR,
    VERITAS_DIR, TOOLS_DIR
)
from tools.hardcoded_path_replacer import replace_paths
from tools.structure_auditor import audit_structure  # ← 明示的に audit_structure を呼ぶ

# === 対象ディレクトリ（v3.0構成）===
TARGETS = [
    DAGS_DIR,
    PLUGINS_DIR,
    SCRIPTS_DIR,
    CORE_DIR,
    STRATEGIES_DIR,
    VERITAS_DIR,
    TOOLS_DIR,
]

def refactor_all():
    print("🚀 Noctria Kingdom Structure Refactor (v3.0)")
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
    audit_structure()

if __name__ == "__main__":
    refactor_all()