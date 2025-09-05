# /mnt/d/noctria_kingdom/tools/fix_import_paths.py

import os
from pathlib import Path

BASE_DIR = Path("/opt/airflow")
REPLACEMENTS = {
    'from core.data.': 'from core.data.',
    'from core.risk_control import': 'from core.risk_control import',
    'from strategies.noctus_sentinella import': 'from strategies.noctus_sentinella import',
    'from scripts.optimize_params_with_optuna import': 'from scripts.optimize_params_with_optuna import',
    'from scripts.evaluate_metaai_model import': 'from scripts.evaluate_metaai_model import',
    'from scripts.apply_best_params_to_metaai import': 'from scripts.apply_best_params_to_metaai import',
    # 念のため strategies から直接も置換
    'from strategies.noctus_sentinella import': 'from strategies.noctus_sentinella import',
}

def fix_imports():
    print("🔧 Import文の修正を開始します...")
    for file in BASE_DIR.rglob("*.py"):
        try:
            content = file.read_text()
        except Exception as e:
            print(f"⚠️ 読み込みエラー: {file} -> {e}")
            continue

        modified = content
        for old, new in REPLACEMENTS.items():
            modified = modified.replace(old, new)

        if modified != content:
            try:
                file.write_text(modified)
                print(f"✅ 修正済: {file.relative_to(BASE_DIR)}")
            except Exception as e:
                print(f"❌ 書き込み失敗: {file} -> {e}")

    print("🎉 Import修正完了！")

if __name__ == "__main__":
    fix_imports()
