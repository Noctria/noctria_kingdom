from core.path_config import CORE_DIR, DAGS_DIR, DATA_DIR, INSTITUTIONS_DIR, LOGS_DIR, MODELS_DIR, PLUGINS_DIR, SCRIPTS_DIR, STRATEGIES_DIR, TESTS_DIR, TOOLS_DIR, VERITAS_DIR
import logging
import sys
from core.path_config import LOGS_DIR

# 📁 ログディレクトリの作成（存在しない場合）
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 🧠 共通ロガーセットアップ関数
def setup_logger(name: str, level=logging.INFO):
    """指定した名前でカスタムロガーを返す"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # コンソール出力
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(name)s - %(message)s')
        stream_handler.setFormatter(stream_formatter)
        logger.addHandler(stream_handler)

        # ファイル出力
        file_handler = logging.FileHandler(LOGS_DIR / "system.log")
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

# 🚨 ルール違反をログ出力する補助関数
def log_violation(message: str):
    """戦略ルール違反などを記録"""
    logger = setup_logger("RuleViolation")
    logger.warning(f"Violation Detected: {message}")

# ✅ 動作確認用
if __name__ == "__main__":
    log_violation("Trade rejected due to daily loss limit exceeded")