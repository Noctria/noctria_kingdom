import os
import logging
from core.utils import setup_logger

def initialize_system():
    """Noctria Kingdomの初期設定を行う"""
    logger = setup_logger("SystemInit")
    logger.info("Noctria Kingdomのシステム初期化を開始")

    # 必要なディレクトリの作成
    required_dirs = ["data/raw_data", "data/processed_data", "logs"]
    for dir in required_dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)
            logger.info(f"ディレクトリ作成: {dir}")

    logger.info("システム初期化完了")

# ✅ システム初期化の実行
if __name__ == "__main__":
    initialize_system()
