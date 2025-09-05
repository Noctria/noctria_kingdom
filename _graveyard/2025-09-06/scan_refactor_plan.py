from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
# tools/scan_refactor_plan.py

import os
import re
import json
from pathlib import Path

# ✅ 共通パス定義（path_config.py から読み込み）
try:
    from core.path_config import BASE_DIR, LOGS_DIR
except ImportError:
    # 単体実行時のためにパス追加
    CURRENT = Path(__file__).resolve()
    BASE_DIR = CURRENT.parents[1]
    LOGS_DIR = BASE_DIR / "airflow_docker" / "logs"

LOG_PATH = LOGS_DIR / "refactor_plan.json"

# 除外ディレクトリ
EXCLUDE_DIRS = {"venv", ".git", "__pycache__", "models", "logs", "tmp"}
TARGET_EXT = ".py"

# 責任区分マップ
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

# ハードコードされていそうなパスのパターン
SUSPECT_PATHS = [
    "strategies/", "execution/", "data/", "models/", "airflow_docker/",
    "veritas/", "llm_server/", "noctria_gui/", "experts/", "tools/", "tests/", "docs/"
]


def is_excluded(path: Path) -> bool:
    """除外対象かどうか判定"""
    return any(part in EXCLUDE_DIRS for part in path.parts)


def classify_responsibility(filename: str) -> str:
    """責任区分を判定"""
    for key, dest in RESPONSIBILITY_MAP.items():
        if key in filename:
            return dest
    return "misc"


def scan_file(path: Path) -> list:
    """ファイル内容をスキャンしてリファクタ候補を抽出"""
    actions = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️ 読み込み失敗: {path} ({e})")
        return actions

    for i, line in enumerate(lines):
        for pattern in SUSPECT_PATHS:
            if pattern in line and "path_config" not in line:
                actions.append({
                    "file": str(path.relative_to(BASE_DIR)),
                    "line": i + 1,
                    "type": "hardcoded_path",
                    "content": line.strip()
                })

        if "def simulate" in line and "strategies/" not in str(path):
            actions.append({
                "file": str(path.relative_to(BASE_DIR)),
                "line": i + 1,
                "type": "simulate_function_out_of_place",
                "content": line.strip()
            })

    return actions


def main():
    """リファクタリング計画のスキャン・出力処理"""
    plan = []

    for root, _, files in os.walk(BASE_DIR):
        root_path = Path(root)
        if is_excluded(root_path.relative_to(BASE_DIR)):
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