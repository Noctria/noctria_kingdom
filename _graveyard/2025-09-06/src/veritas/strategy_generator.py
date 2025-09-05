# src/veritas/strategy_generator.py

import sys
from pathlib import Path

# --- ここで src ディレクトリの絶対パスを sys.path に追加 ---
src_path = Path(__file__).resolve().parents[1]  # src/veritas/ の一つ上 = src/
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import os
import torch
import psycopg2
from datetime import datetime
from typing import Optional

from core.path_config import VERITAS_MODELS_DIR, STRATEGIES_DIR, LOGS_DIR
from core.logger import setup_logger

from veritas.models.ml_model.simple_model import SimpleModel

logger = setup_logger("VeritasGenerator", LOGS_DIR / "veritas" / "generator.log")

# --- 環境変数（必要に応じてcore.settingsへ集約してもOK） ---
DB_NAME = os.getenv("POSTGRES_DB", "airflow")
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

MODEL_PATH: Path = Path(os.getenv("VERITAS_MODEL_DIR", str(VERITAS_MODELS_DIR / "ml_model")))

def load_ml_model() -> SimpleModel:
    """
    PyTorchモデル（SimpleModel構造）をロードする
    """
    if not MODEL_PATH.exists():
        logger.error(f"❌ MLモデルディレクトリが存在しません: {MODEL_PATH}")
        raise FileNotFoundError(f"ML model directory not found: {MODEL_PATH}")
    model_file = MODEL_PATH / "model.pt"
    if not model_file.is_file():
        logger.error(f"❌ モデルファイルが見つかりません: {model_file}")
        raise FileNotFoundError(f"Model file not found: {model_file}")
    model = SimpleModel()
    try:
        state_dict = torch.load(str(model_file), map_location=torch.device('cpu'))
        model.load_state_dict(state_dict)
        model.eval()
        logger.info("✅ MLモデルのロード完了")
        return model
    except Exception as e:
        logger.error(f"モデルロード失敗: {e}", exc_info=True)
        raise

def build_prompt(symbol: str, tag: str, target_metric: str) -> str:
    """
    戦略生成用プロンプトまたはパラメータ説明
    """
    prompt = f"通貨ペア'{symbol}', 特性'{tag}', 目標指標'{target_metric}'に基づく取引戦略生成用パラメータ"
    logger.info(f"📝 生成されたパラメータ説明: {prompt}")
    return prompt

def generate_strategy_code(prompt: str) -> str:
    """
    MLモデルを使った戦略コード生成
    （本番用は推論結果→Python戦略コードへ動的変換が必要）
    """
    try:
        model = load_ml_model()
        # TODO: 入力ベクトル・推論ロジックを本番仕様で置き換え
        import random
        random.seed(len(prompt))
        dummy_code = f"# Generated strategy code for prompt: {prompt}\n"
        dummy_code += f"def simulate():\n    return {random.uniform(0, 1):.4f}  # 戦略のスコア例\n"
        logger.info("🤖 MLモデルによる戦略コードの生成完了（ダミー）")
        return dummy_code
    except Exception as e:
        logger.error(f"戦略コード生成失敗: {e}", exc_info=True)
        raise

def save_to_db(prompt: str, response: str) -> None:
    """
    生成結果をPostgreSQL DBへ保存
    """
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO veritas_outputs (prompt, response, created_at) VALUES (%s, %s, %s)",
                (prompt, response, datetime.now())
            )
            conn.commit()
        logger.info("✅ 生成結果をDBに保存しました。")
    except Exception as e:
        logger.error(f"🚨 DB保存に失敗: {e}", exc_info=True)
        # 必要に応じてファイル等へバックアップ実装可
    finally:
        if conn:
            conn.close()

def save_to_file(code: str, tag: str) -> str:
    """
    生成コードをファイル保存し、保存パスを返却
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"veritas_{tag}_{now}.py"
    save_dir = STRATEGIES_DIR / "veritas_generated"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(code)
        logger.info(f"💾 戦略をファイルに保存しました: {save_path}")
    except Exception as e:
        logger.error(f"戦略ファイル保存失敗: {e}", exc_info=True)
        raise
    return str(save_path)

# ✅ テストブロック（本番DAG等からは直接呼ばれない）
if __name__ == "__main__":
    # テスト用プロンプトでのダミー生成例
    test_prompt = build_prompt("USDJPY", "hybrid", "sharpe_ratio")
    code = generate_strategy_code(test_prompt)
    save_path = save_to_file(code, "hybrid")
    print(f"戦略コードの保存先: {save_path}")
    save_to_db(test_prompt, code)
    print("DB保存まで完了")
