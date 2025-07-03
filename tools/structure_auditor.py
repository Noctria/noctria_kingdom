# tools/structure_refactor.py

from pathlib import Path
import os

from core.path_config import (
    DAGS_DIR, PLUGINS_DIR, SCRIPTS_DIR, CORE_DIR, STRATEGIES_DIR,
    VERITAS_DIR, TOOLS_DIR
)
from tools.hardcoded_path_replacer import replace_paths

# === 対象ディレクトリ（v3.0対応）===
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
    audit_main()

if __name__ == "__main__":
    refactor_all()
