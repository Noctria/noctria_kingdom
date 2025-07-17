#!/usr/bin/env python3
# coding: utf-8

"""
👑 Noctria Kingdom Core Package Initializer
- このパッケージが読み込まれた際の初期化処理を定義
"""

# ✅ 修正: 絶対パス 'core.' から、相対パス '.' にインポート方法を変更
# これにより、パッケージ初期化時の循環参照的なエラーを防ぐ
from .utils import setup_logger
from .path_config import RAW_DATA_DIR, PROCESSED_DATA_DIR, LOGS_DIR

def initialize_system():
    """Noctria Kingdomのシステム初期化を行う（現在はディレクトリ作成のみ）"""
    logger = setup_logger("SystemInit")
    logger.info("Noctria Kingdomのシステム初期化を開始")

    # 必要なディレクトリの作成（path_configで一元管理）
    required_dirs = [
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        LOGS_DIR
    ]
    for dir_path in required_dirs:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 ディレクトリ作成: {dir_path}")

    logger.info("✅ システム初期化完了")

# ✅ システム初期化の実行（スクリプトとして直接呼ばれた場合のみ）
if __name__ == "__main__":
    initialize_system()
