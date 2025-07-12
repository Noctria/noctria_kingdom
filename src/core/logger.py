# core/logger.py

import logging
import sys
from pathlib import Path
from core.path_config import LOGS_DIR


def setup_logger(name: str, log_file: Path, level=logging.INFO) -> logging.Logger:
    """
    任意のログファイルに対して名前付きロガーを設定。
    二重ハンドラ追加を防ぐため、既に設定されていれば再利用。
    """
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    logger.setLevel(level)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 📁 ファイル出力ハンドラ
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 🖥 コンソール出力ハンドラ
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def log_violation(message: str):
    """
    戦略ルール違反などを violations.log に記録
    """
    violation_log_file = LOGS_DIR / "violations.log"
    logger = setup_logger("RuleViolationLogger", violation_log_file)
    logger.warning(f"Violation Detected: {message}")


# ✅ 手動実行テスト
if __name__ == "__main__":
    test_log_path = LOGS_DIR / "test_run.log"
    logger = setup_logger("TestLogger", test_log_path)

    logger.info("✅ ログ出力テスト開始")
    log_violation("⚠️ テスト: リスク制限を超過した取引が発生")
    logger.info("✅ ログ出力テスト終了")

    print(f"ログ出力先: {test_log_path}")
