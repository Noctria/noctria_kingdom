import logging
import os

def setup_logger(name: str, log_file: str, level=logging.INFO, to_stdout: bool = False):
    """
    指定した名前のロガーを作成して返す。
    - name: ロガーの名前（ユニークであること）
    - log_file: 出力ファイルパス
    - level: ログレベル
    - to_stdout: Trueにするとコンソールにも出力
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)

        if to_stdout:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(stream_handler)

    return logger

def log_violation(message: str, log_file: str = None):
    """
    ルール違反や異常を共通で記録する関数
    """
    if log_file is None:
        airflow_home = os.getenv("AIRFLOW_HOME", "/opt/airflow")
        log_file = os.path.join(airflow_home, "logs", "ViolationLogger.log")

    logger = setup_logger("ViolationLogger", log_file)
    logger.warning(f"Violation Detected: {message}")
