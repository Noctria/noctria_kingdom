# core/logger.py

import logging
import os

def setup_logger(name: str, log_file: str = "/opt/airflow/logs/system.log", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # ディレクトリ作成
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # ファイルハンドラ（Airflowでも有効）
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # コンソール出力（Airflow Web UIにも出る）
        sh = logging.StreamHandler()
        sh.setLevel(level)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    return logger

def log_violation(message):
    logger = setup_logger("ViolationLogger")
    logger.warning(f"Violation Detected: {message}")
