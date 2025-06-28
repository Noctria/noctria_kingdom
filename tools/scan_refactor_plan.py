# tools/scan_refactor_plan.py

import os
import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = PROJECT_ROOT / "logs" / "refactor_plan.json"
EXCLUDE_DIRS = {"venv", ".git", "__pycache__", "models", "logs", "tmp"}
TARGET_EXT = ".py"

RESPONSIBILITY_MAP = {
    "generate": "veritas/generate",
    "evaluate": "veritas/evaluate",
    "interface": "veritas/interface",
    "templates": "veritas/templates",
    "utils": "veritas/utils",
    "core": "core",
    "execution": "execution",
    "airflow_docker": "airflow_docker",
}

SUSPECT_PATHS = [
    "strategies/", "execution/", "data/", "models/", "airflow_docker/",
    "veritas/", "llm_server/", "noctria_gui/", "experts/", "tools/", "tests/", "docs/"
]

def is_excluded(path: Path):
    return any(part in EXCLUDE_DIRS for part in path.parts)

def classify_responsibility(filename: str):
    for key, dest in RESPONSIBILITY_MAP.items():
        if key in filename:
            return dest
    return "misc"

def scan_file(path: Path):
    actions = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        for pattern in SUSPECT_PATHS:
            if pattern in line and "path_config" not in line:
                actions.append({
                    "file": str(path.relative_to(PROJECT_ROOT)),
                    "line": i + 1,
                    "type": "hardcoded_path",
                    "content": line.strip()
                })

        if "def simulate" in line and "strategies/" not in str(path):
            actions.append({
                "file": str(path.relative_to(PROJECT_ROOT)),
                "line": i + 1,
                "type": "simulate_function_out_of_place",
                "content": line.strip()
            })

    return actions

def main():
    plan = []

    for root, _, files in os.walk(PROJECT_ROOT):
        root_path = Path(root)
        if is_excluded(root_path.relative_to(PROJECT_ROOT)):
            continue
        for file in files:
            if file.endswith(TARGET_EXT):
                path = root_path / file
                responsibility = classify_responsibility(str(path))
                issues = scan_file(path)
                for issue in issues:
                    issue["suggested_dir"] = responsibility
                plan.extend(issues)

    os.makedirs(LOG_PATH.parent, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(f"📋 リファクタ計画を {LOG_PATH} に出力しました（検出件数: {len(plan)}）")

if __name__ == "__main__":
    main()
