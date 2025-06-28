import os
import re
import json
import shutil
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
PLAN_PATH = LOG_DIR / "refactor_plan.json"
APPLIED_LOG = LOG_DIR / "refactor_applied.json"
TARGET_EXT = ".py"
EXCLUDE_DIRS = {"venv", ".git", "__pycache__", "models", "logs", "tmp"}

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

# === Mode: scan ===
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

def run_scan():
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
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"📋 リファクタ計画を {PLAN_PATH} に出力（検出件数: {len(plan)}）")

# === Mode: apply ===
def run_apply():
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        actions = json.load(f)
    applied = []
    for action in actions:
        file_path = PROJECT_ROOT / action["file"]
        if not file_path.exists():
            continue
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
        if action["type"] == "simulate_function_out_of_place":
            dest_dir = PROJECT_ROOT / "veritas" / "utils"
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(dest_dir / file_path.name))
            applied.append(action)
    with open(APPLIED_LOG, "w", encoding="utf-8") as f:
        json.dump(applied, f, indent=2, ensure_ascii=False)
    print(f"✅ リファクタ適用完了（{len(applied)}件）→ {APPLIED_LOG}")

# === Mode: restructure ===
def run_restructure():
    base = PROJECT_ROOT / "veritas"
    for sub in ["generate", "evaluate", "interface", "utils", "templates"]:
        (base / sub).mkdir(parents=True, exist_ok=True)
    print("🏗️ Veritas ディレクトリ構造を再構成しました")

# === Mode: rewrite_dags ===
def run_rewrite_dags():
    dags_dir = PROJECT_ROOT / "airflow_docker" / "dags"
    for path in dags_dir.glob("*.py"):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if "@dag" in content and "PythonOperator" in content:
            new_content = re.sub(
                r"PythonOperator\(.*?python_callable *= *(\w+).*?\)",
                r"PythonOperator(task_id='external_task', python_callable=lambda: subprocess.run(['python3', 'scripts/\1.py']))",
                content,
                flags=re.DOTALL
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"🔄 外部スクリプト呼び出しに変更: {path.name}")

# === Mode: generate_tests ===
def run_generate_tests():
    tests_dir = PROJECT_ROOT / "tests"
    tests_dir.mkdir(exist_ok=True)
    example = tests_dir / "test_veritas_generate.py"
    if not example.exists():
        with open(example, "w", encoding="utf-8") as f:
            f.write("""import unittest\nfrom veritas.generate.strategy_generator import generate_strategy\n\nclass TestStrategyGenerator(unittest.TestCase):\n    def test_generate(self):\n        filename = generate_strategy('test')\n        self.assertTrue(filename.endswith('.py'))""")
        print("🧪 tests/ テンプレートを生成しました")

# === Entrypoint ===
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["scan", "apply", "restructure", "rewrite_dags", "generate_tests"])
    args = parser.parse_args()

    if args.mode == "scan":
        run_scan()
    elif args.mode == "apply":
        run_apply()
    elif args.mode == "restructure":
        run_restructure()
    elif args.mode == "rewrite_dags":
        run_rewrite_dags()
    elif args.mode == "generate_tests":
        run_generate_tests()

if __name__ == "__main__":
    main()
