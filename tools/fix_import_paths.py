import os
from pathlib import Path

# 📌 修正対象のベースディレクトリ（Airflow Docker環境内）
BASE_DIR = Path("/opt/airflow")
TARGET_EXTENSIONS = [".py"]

# 🔁 修正対象の import 文と修正後の内容（順序重要）
REPLACEMENTS = {
    'from data.': 'from core.data.',
    'from risk_control import': 'from core.risk_control import',
    'from noctus_sentinella import': 'from strategies.noctus_sentinella import',
    'from evaluate_metaai_model import': 'from scripts.evaluate_metaai_model import',
    'from optimize_params_with_optuna import': 'from scripts.optimize_params_with_optuna import',
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
