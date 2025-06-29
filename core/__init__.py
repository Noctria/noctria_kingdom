# core/__init__.py

import logging
from core.utils import setup_logger
from core.path_config import RAW_DATA_DIR, PROCESSED_DATA_DIR, AIRFLOW_LOG_DIR

def initialize_system():
    """Noctria Kingdomの初期設定を行う"""
    logger = setup_logger("SystemInit")
    logger.info("Noctria Kingdomのシステム初期化を開始")

    # 必要なディレクトリの作成（path_configで一元管理）
    required_dirs = [RAW_DATA_DIR, PROCESSED_DATA_DIR, AIRFLOW_LOG_DIR]
    for dir_path in required_dirs:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 ディレクトリ作成: {dir_path}")

    logger.info("✅ システム初期化完了")

# ✅ システム初期化の実行
if __name__ == "__main__":
    initialize_system()
