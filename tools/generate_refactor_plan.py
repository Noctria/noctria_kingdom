# tools/generate_refactor_plan.py

import os
import json
from pathlib import Path
from core.path_config import BASE_DIR

# === 分類用カテゴリ ===
CATEGORY_RULES = {
    "delete": ["__pycache__", ".pytest_cache", ".ipynb_checkpoints", "venv", "testenv"],
    "duplicate": ["core", "scripts", "strategies", "data", "models", "logs", "config", "dags"],
    "git_internal": [".git", ".git/logs", ".git/refs", ".git/objects", ".git/info"],
    "keep": ["airflow_docker", "veritas", "core", "execution", "experts", "tools", "llm_server", "noctria_gui", "tests"],
}

def classify_directory(path: Path) -> str:
    name = path.name.lower()

    if any(name == rule for rule in CATEGORY_RULES["delete"]):
        return "delete"

    if any(name == rule for rule in CATEGORY_RULES["duplicate"]):
        return "duplicate"

    if any(str(path).startswith(str(BASE_DIR / git_dir)) for git_dir in CATEGORY_RULES["git_internal"]):
        return "git_internal"

    if any(name == rule for rule in CATEGORY_RULES["keep"]):
        return "keep"

    return "other"

def generate_plan():
    plan = {"delete": [], "duplicate": [], "git_internal": [], "other": []}
    all_dirs = list(BASE_DIR.rglob("*"))

    for path in all_dirs:
        if path.is_dir():
            category = classify_directory(path)
            if category != "keep":
                plan[category].append(str(path))

    # 保存
    out_path = BASE_DIR / "logs" / "refactor_plan.json"
    os.makedirs(out_path.parent, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(f"✅ リファクタ計画出力: {out_path} に {sum(len(v) for v in plan.values())} 件分類")

if __name__ == "__main__":
    generate_plan()
