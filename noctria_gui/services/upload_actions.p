import subprocess
import shutil
from pathlib import Path

# 共通スクリプトパス
SCRIPT_EVAL = Path("veritas/evaluate_veritas.py")
SCRIPT_DO = Path("execution/generate_order_json.py")

UPLOAD_LOG_DIR = Path("logs/uploads")
STRATEGY_DIR = Path("strategies/official/")

def re_evaluate_strategy(strategy_id: str):
    """
    特定のアップロード戦略を再評価し、採用ならEA命令を再出力する
    """
    dir_path = UPLOAD_LOG_DIR / strategy_id
    py_files = list(dir_path.glob("*.py"))

    if not py_files:
        raise FileNotFoundError(f"No .py strategy file found in {dir_path}")

    strategy_file = py_files[0]

    # official に一時コピー（評価スクリプトの前提）
    official_path = STRATEGY_DIR / strategy_file.name
    shutil.copy(strategy_file, official_path)

    # 評価スクリプト実行
    subprocess.run(["python", str(SCRIPT_EVAL)], check=True)

    # 採用されていれば命令JSONを再出力
    subprocess.run(["python", str(SCRIPT_DO)], check=True)

def delete_strategy_log(strategy_id: str):
    """
    特定のアップロード戦略ログディレクトリを削除する
    """
    dir_path = UPLOAD_LOG_DIR / strategy_id
    if dir_path.exists() and dir_path.is_dir():
        shutil.rmtree(dir_path)
