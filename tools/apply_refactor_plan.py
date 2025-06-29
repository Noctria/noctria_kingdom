# tools/apply_refactor_plan.py

import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = PROJECT_ROOT / "logs" / "refactor_plan.json"
APPLIED_LOG = PROJECT_ROOT / "logs" / "refactor_applied.json"

def load_plan():
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def apply_refactor(actions):
    applied = []
    for action in actions:
        file_path = PROJECT_ROOT / action["file"]
        if not file_path.exists():
            continue

        # ハードコード書き換え
        if action["type"] == "hardcoded_path":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "from core.path_config" not in content:
                content = f"from core.path_config import *\n\n{content}"
            for raw in ["strategies/", "data/", "execution/", "models/"]:
                if raw in content:
                    content = content.replace(f'"{raw}', f'{raw.upper().replace("/", "_")}_DIR / "')
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            applied.append(action)

        # simulate関数を utils/ に移動
        if action["type"] == "simulate_function_out_of_place":
            dest_dir = PROJECT_ROOT / "veritas" / "utils"
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(dest_dir / file_path.name))
            applied.append(action)

    with open(APPLIED_LOG, "w", encoding="utf-8") as f:
        json.dump(applied, f, indent=2, ensure_ascii=False)

    print(f"✅ リファクタ適用完了（{len(applied)}件）→ {APPLIED_LOG}")

def main():
    actions = load_plan()
    apply_refactor(actions)

if __name__ == "__main__":
    main()
