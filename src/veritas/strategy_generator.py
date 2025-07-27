# src/veritas/strategy_generator.py

import os
import torch
import psycopg2
from datetime import datetime
from core.path_config import VERITAS_MODELS_DIR, STRATEGIES_DIR, LOGS_DIR
from core.logger import setup_logger

# --- 専門家の記録係をセットアップ ---
logger = setup_logger("VeritasGenerator", LOGS_DIR / "veritas" / "generator.log")

# --- 環境変数 (core.settings に集約するのが望ましい) ---
DB_NAME = os.getenv("POSTGRES_DB", "airflow")
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# MLモデルのパスをenv変数かデフォルトで指定
MODEL_PATH = os.getenv("VERITAS_MODEL_DIR", str(VERITAS_MODELS_DIR / "ml_model"))

def load_ml_model():
    """MLモデルをロードする（実際のモデルによって実装は変わる）"""
    if not os.path.exists(MODEL_PATH):
        logger.error(f"❌ MLモデルディレクトリが存在しません: {MODEL_PATH}")
        raise FileNotFoundError(f"ML model directory not found: {MODEL_PATH}")
    
    logger.info(f"🧠 MLモデルをロード中: {MODEL_PATH}")
    # 例：PyTorchモデルのロード（モデルファイル名は適宜調整）
    model_file = os.path.join(MODEL_PATH, "model.pt")
    if not os.path.isfile(model_file):
        logger.error(f"❌ モデルファイルが見つかりません: {model_file}")
        raise FileNotFoundError(f"Model file not found: {model_file}")

    model = torch.load(model_file, map_location=torch.device('cpu'))
    model.eval()
    logger.info("✅ MLモデルのロード完了")
    return model

def build_prompt(symbol: str, tag: str, target_metric: str) -> str:
    """
    MLモデル用のパラメータ生成または説明文字列を作る。
    MLモデルはプロンプト不要な場合、この関数は単にパラメータ説明を返すなどに書き換えてください。
    """
    prompt = f"通貨ペア'{symbol}', 特性'{tag}', 目標指標'{target_metric}'に基づく取引戦略生成用のパラメータ"
    logger.info(f"📝 生成されたパラメータ説明: {prompt}")
    return prompt

def generate_strategy_code(prompt: str) -> str:
    """
    MLモデルを使って戦略コードや戦略パラメータを生成する関数の雛形。
    実際の推論ロジックはモデル仕様に合わせて実装してください。
    """
    model = load_ml_model()

    # ダミーの推論例：promptの長さを特徴量にして乱数生成でコード文字列を返す（実際は推論結果をコード化）
    import random
    random.seed(len(prompt))
    dummy_code = f"# Generated strategy code for prompt: {prompt}\n"
    dummy_code += f"def simulate():\n    return {random.uniform(0, 1):.4f}  # 戦略のスコア例\n"

    logger.info("🤖 MLモデルによる戦略コードの生成完了（ダミー）")
    return dummy_code

def save_to_db(prompt: str, response: str):
    """生成結果をPostgreSQLに保存する"""
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
        raise
    finally:
        if conn:
            conn.close()

def save_to_file(code: str, tag: str) -> str:
    """生成されたコードをファイルに保存し、ファイルパスを返す"""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"veritas_{tag}_{now}.py"
    save_dir = STRATEGIES_DIR / "veritas_generated"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename

    with open(save_path, "w", encoding="utf-8") as f:
        f.write(code)
        
    logger.info(f"💾 戦略をファイルに保存しました: {save_path}")
    return str(save_path)
