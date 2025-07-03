import os
import sys
import importlib.util
from pathlib import Path

# === パス初期化 ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_DIRS = ["airflow_docker/dags", "scripts", "core"]
DELETE_LIST = [
    "airflow_docker/config/dammy",
    "airflow_docker/dags/dummyfile",
    "airflow_docker/plugins/dammy",
    "strategies/veritas_generated/dammy",
    "veritas_dev/dammy"
]

# === dynamic import for hardcoded_path_replacer.py ===
replacer_path = PROJECT_ROOT / "tools" / "hardcoded_path_replacer.py"
spec = importlib.util.spec_from_file_location("hardcoded_path_replacer", replacer_path)
replacer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replacer)

# === 処理開始 ===
print("🔧 Noctria構造リファクタリング開始...")

# 不要ファイル削除
for rel_path in DELETE_LIST:
    full_path = PROJECT_ROOT / rel_path
    if full_path.exists() and full_path.is_file():
        full_path.unlink()
        print(f"🗑️ Deleted: {rel_path}")
    else:
        print(f"⚠️ Skip (not found): {rel_path}")

# パス自動置換
for rel_dir in TARGET_DIRS:
    full_dir = PROJECT_ROOT / rel_dir
    if not full_dir.exists():
        print(f"⚠️ Directory not found: {rel_dir}")
        continue

    for path in full_dir.rglob("*.py"):
        try:
            replacer.replace_paths(path)
            print(f"✅ Replaced: {path.relative_to(PROJECT_ROOT)}")
        except Exception as e:
            print(f"❌ Failed to process {path.relative_to(PROJECT_ROOT)} → {e}")

print("🎉 リファクタリング完了")
