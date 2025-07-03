# tools/structure_refactor.py

import os
import sys
import shutil
from pathlib import Path

# 📌 現在のスクリプトファイルの絶対パスとプロジェクトルートを取得
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parent.parent
TOOLS_DIR = ROOT_DIR / "tools"

# 🔧 tools ディレクトリをインポートパスに追加してモジュール読み込みを可能にする
sys.path.insert(0, str(TOOLS_DIR))

from hardcoded_path_replacer import replace_paths

# === 基本構成 ===
REPLACE_TARGET_DIRS = [
    "airflow_docker/dags",
    "scripts",
    "veritas",
    "core",
    "tests",
]

UNNECESSARY_PATHS = [
    "airflow_docker/config/dammy",
    "airflow_docker/dags/dummyfile",
    "airflow_docker/plugins/dammy",
    "strategies/veritas_generated/dammy",
    "veritas_dev/dammy",
]

def refactor_structure():
    print("🛠 Noctria Kingdom v2.0 リファクタリング開始\n")

    # === パスの自動置換 ===
    for rel_path in REPLACE_TARGET_DIRS:
        abs_path = ROOT_DIR / rel_path
        if not abs_path.exists():
            continue
        print(f"🔍 変換中: {abs_path}")
        for dirpath, _, filenames in os.walk(abs_path):
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                file_path = Path(dirpath) / fname
                replace_paths(file_path)

    # === 不要ファイルの削除 ===
    print("\n🧹 不要ファイルの削除:")
    for rel_path in UNNECESSARY_PATHS:
        abs_path = ROOT_DIR / rel_path
        if abs_path.exists():
            abs_path.unlink()
            print(f"🗑 削除: {abs_path}")
        else:
            print(f"✅ 存在しない: {abs_path}")

    print("\n✅ 構造リファクタ完了")

if __name__ == "__main__":
    refactor_structure()
