# ✅ core/logger.py

import logging
import os

def setup_logger(name: str, log_file: str, level=logging.INFO):
    """
    指定した名前のロガーを作成して返す。
    - name: ロガーの名前
    - log_file: 出力ファイルパス（例: /opt/airflow/logs/AurusLogger.log）
    - level: ログレベル（デフォルト: INFO）
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)

        logger.addHandler(file_handler)

    return logger

def log_violation(message: str, log_file: str = "/opt/airflow/logs/ViolationLogger.log"):
    """
    ルール違反や異常を共通で記録する関数
    """
    logger = setup_logger("ViolationLogger", log_file)
    logger.warning(f"Violation Detected: {message}")
