from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
# tools/apply_refactor_plan.py

import os
import json
import shutil
from pathlib import Path

# ✅ パス一元管理
try:
    from core.path_config import BASE_DIR, LOGS_DIR
except ImportError:
    BASE_DIR = Path(__file__).resolve().parents[1]
    LOGS_DIR = BASE_DIR / "airflow_docker" / "logs"

PLAN_PATH = LOGS_DIR / "refactor_plan.json"

def load_plan(path: Path) -> list:
    if not path.exists():
        print(f"❌ No refactor plan found at {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def apply_refactor_step(src: str, dst: str):
    abs_src = BASE_DIR / src
    abs_dst = BASE_DIR / dst

    if not abs_src.exists():
        print(f"⚠️ Not found: {src}")
        return

    os.makedirs(abs_dst.parent, exist_ok=True)
    shutil.move(str(abs_src), str(abs_dst))
    print(f"📁 Moved: {src} → {dst}")

    update_references(src, dst)

def update_references(old_path: str, new_path: str):
    all_py_files = list(BASE_DIR.rglob("*.py"))
    old_import = path_to_import(old_path)
    new_import = path_to_import(new_path)

    for file in all_py_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️ Skipping unreadable file: {file} ({e})")
            continue

        if old_import in content or old_path in content:
            new_content = content.replace(old_import, new_import).replace(old_path, new_path)
            with open(file, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"✏️ Updated import in: {file.relative_to(BASE_DIR)}")

def path_to_import(path: str) -> str:
    return path.replace("/", ".").replace(".py", "")

def main():
    plan = load_plan(PLAN_PATH)
    if not plan:
        return

    print(f"🧠 Applying {len(plan)} refactor steps...")
    for step in plan:
        src = step.get("file")
        suggested = step.get("suggested_dir")
        if src and suggested:
            dst = str(Path(suggested) / Path(src).name)
            apply_refactor_step(src, dst)
    print("✅ Refactoring complete!")

if __name__ == "__main__":
    main()