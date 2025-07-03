# ================================
# 🏗️ Noctria Kingdom 構造再構成スクリプト
# - v2.0準拠のリファクタリング自動処理
# - 不要ファイルの削除 + パス自動置換
# ================================

import os
import sys
import shutil
from pathlib import Path

# ✅ プロジェクトルートを sys.path に追加
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from tools.hardcoded_path_replacer import replace_paths

# 📦 不要ファイル/ディレクトリの削除対象
REMOVE_TARGETS = [
    "airflow_docker/config/dammy",
    "airflow_docker/dags/dummyfile",
    "airflow_docker/plugins/dammy",
    "strategies/veritas_generated/dammy",
    "veritas_dev/dammy"
]

# 🎯 パス自動置換対象ディレクトリ
REPLACE_TARGET_DIRS = [
    "airflow_docker/dags",
    "scripts",
    "core",
    "veritas",
]

def remove_unnecessary_files():
    print("🧹 不要ファイル削除中...")
    for target in REMOVE_TARGETS:
        path = ROOT_DIR / target
        if path.exists():
            if path.is_file():
                path.unlink()
                print(f"  ✅ 削除: {path}")
            elif path.is_dir():
                shutil.rmtree(path)
                print(f"  ✅ ディレクトリ削除: {path}")
        else:
            print(f"  ⚠️ スキップ（存在しない）: {path}")

def replace_hardcoded_paths():
    print("🔧 パスの自動置換を開始...")
    for target_dir in REPLACE_TARGET_DIRS:
        base = ROOT_DIR / target_dir
        if not base.exists():
            print(f"  ⚠️ スキップ（存在しない）: {base}")
            continue

        for py_file in base.rglob("*.py"):
            try:
                replace_paths(py_file)
                print(f"  🔄 置換済: {py_file}")
            except Exception as e:
                print(f"  ❌ エラー: {py_file} -> {e}")

def main():
    print("🚀 Noctria Kingdom v2.0 構造整備 開始")
    remove_unnecessary_files()
    replace_hardcoded_paths()
    print("🎉 全処理完了")

if __name__ == "__main__":
    main()
