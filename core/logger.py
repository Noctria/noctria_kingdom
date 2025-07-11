# core/logger.py

import logging
import sys
from core.path_config import LOGS_DIR

# 🧠 共通ロガーセットアップ関数
def setup_logger(name: str, log_file, level=logging.INFO):
    """
    指定した名前とファイルパスでカスタムロガーをセットアップする。
    同じ名前でハンドラが既に設定済みの場合は、既存のロガーを返す。
    """
    logger = logging.getLogger(name)
    
    # ハンドラが既に設定されている場合は、既存のロガーを返す（二重設定を防止）
    if logger.hasHandlers():
        return logger

    logger.setLevel(level)

    # ログファイルのディレクトリが存在しない場合は作成
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # フォーマッタの作成
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # -------------------
    # 1. ファイル出力ハンドラ
    # -------------------
    # 引数で受け取ったlog_fileに出力するように修正
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # -------------------
    # 2. コンソール出力ハンドラ
    # -------------------
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

# 🚨 ルール違反をログ出力する補助関数
def log_violation(message: str):
    """戦略ルール違反などを専用ログに記録"""
    # 違反ログ専用のファイルパスを指定する
    violation_log_file = LOGS_DIR / "violations.log"
    logger = setup_logger("RuleViolationLogger", violation_log_file)
    logger.warning(f"Violation Detected: {message}")

# ✅ 動作確認用
if __name__ == "__main__":
    # テスト用のログファイルパスを指定
    test_log_path = LOGS_DIR / "test_run.log"
    main_logger = setup_logger("MainTest", test_log_path)
    
    main_logger.info("ロガーのテストを開始します。")
    log_violation("Trade rejected due to daily loss limit exceeded")
    main_logger.info("ロガーのテストが完了しました。")
    print(f"ログが出力されました: {test_log_path}, {LOGS_DIR / 'violations.log'}")
