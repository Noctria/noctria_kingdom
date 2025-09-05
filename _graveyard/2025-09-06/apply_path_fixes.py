import os
from pathlib import Path

# 設定
ROOT = Path("/opt/airflow")
OLD_PATH = "/mnt/e/"
NEW_PATH = "/mnt/d/"
TARGET_FILES = [
    "20250603.md",
    "AirFlow_start.md",
    "callmemo_20250602.md",
    "カスタムAirflowイメージを作る.md",
    "tools/scan_and_fix_paths.py",
    "veritas/veritas_generate_strategy.py",
    "airflow_docker/pvc/airflow-dags-pv.yaml",
    "airflow_docker/pvc/airflow-dags-pvc.yaml",
    "airflow_docker/scripts/download_veritas_model.py",
    "airflow_docker/scripts/push_generated_strategy.py"
]

def apply_fixes(file_path: Path):
    full_path = ROOT / file_path
    if not full_path.exists():
        print(f"❌ ファイルが見つかりません: {file_path}")
        return
    try:
        content = full_path.read_text(encoding="utf-8")
        if OLD_PATH not in content:
            print(f"✅ 対象パスなし（スキップ）: {file_path}")
            return
        new_content = content.replace(OLD_PATH, NEW_PATH)
        backup_path = full_path.with_suffix(full_path.suffix + ".bak")
        full_path.rename(backup_path)
        full_path.write_text(new_content, encoding="utf-8")
        print(f"🛠 修正済: {file_path} → バックアップ: {backup_path.name}")
    except Exception as e:
        print(f"⚠️ エラー（{file_path}）: {e}")

if __name__ == "__main__":
    print("🚀 パス修正開始\n")
    for rel_path in TARGET_FILES:
        apply_fixes(Path(rel_path))
    print("\n✅ すべての処理が完了しました。")
