# core/logger.py

import logging
import os

# ✅ ログ出力先の絶対パス（Airflowコンテナ用）
LOG_DIR = "/opt/airflow/logs"
LOG_FILE = os.path.join(LOG_DIR, "system.log")

# ✅ ログディレクトリの自動作成
os.makedirs(LOG_DIR, exist_ok=True)

# ✅ ログ設定（1度だけ実行）
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ✅ 共通ロガーの取得
logger = logging.getLogger("NoctriaLogger")

def log_info(message):
    """ 情報ログを出力 """
    logger.info(message)

def log_warning(message):
    """ 警告ログを出力 """
    logger.warning(message)

def log_violation(message):
    """ ルール違反ログ（警告） """
    logger.warning(f"Violation Detected: {message}")

def log_error(message):
    """ エラーログ """
    logger.error(message)
