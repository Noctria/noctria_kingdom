from pathlib import Path
import shutil
import datetime
import subprocess

from core.path_config import STRATEGIES_DIR

# ディレクトリ定義
UPLOADED_DIR = STRATEGIES_DIR / "uploaded"
OFFICIAL_DIR = STRATEGIES_DIR / "official"

def list_uploaded_strategies():
    """アップロード済戦略をリスト形式で返す"""
    return sorted([f.name for f in UPLOADED_DIR.glob("*.py")])

def delete_uploaded_strategy(filename: str) -> bool:
    """アップロード済み戦略を削除"""
    target = UPLOADED_DIR / filename
    if target.exists():
        target.unlink()
        return True
    return False

def re_evaluate_strategy(filename: str) -> dict:
    """
    特定のアップロード済み戦略を一時評価。
    veritas/evaluate_veritas.py をサブプロセスで呼ぶ。
    """
    strategy_path = UPLOADED_DIR / filename
    if not strategy_path.exists():
        return {"success": False, "message": f"{filename} が存在しません"}

    try:
        result = subprocess.run(
            ["python", "veritas/evaluate_veritas.py", "--strategy", str(strategy_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

def promote_to_official(filename: str) -> bool:
    """
    アップロード戦略を official/ に昇格コピーする
    （上書きあり）
    """
    src = UPLOADED_DIR / filename
    dst = OFFICIAL_DIR / filename
    if src.exists():
        shutil.copy2(src, dst)
        return True
    return False

def save_uploaded_strategy(file_bytes: bytes, filename: str) -> str:
    """
    アップロードされたファイルを uploaded/ に保存し、ファイル名を返す
    """
    sanitized_name = Path(filename).name  # パス注入防止
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_name = f"{now}_{sanitized_name}"
    target_path = UPLOADED_DIR / target_name
    with open(target_path, "wb") as f:
        f.write(file_bytes)
    return target_name
