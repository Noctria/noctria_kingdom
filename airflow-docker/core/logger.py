import logging
import os

def setup_logger(name: str, log_file: str = "/opt/airflow/logs/system.log", level=logging.INFO):
    """
    指定した名前のロガーを作成して返す。
    - name: ロガーの名前（モジュール単位で付与）
    - log_file: ログ出力先ファイルのパス
    - level: ログレベル（デフォルトはINFO）
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 既にハンドラが追加されていれば再追加しない
    if not logger.handlers:
        # ログフォルダが存在しない場合は作成
        log_dir = os.path.dirname(log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # ファイルハンドラを設定
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)

        # フォーマットを設定
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)

        # ハンドラ追加
        logger.addHandler(fh)

    return logger

def log_violation(message):
    """戦略違反・異常系の共通ログ関数"""
    logger = setup_logger("ViolationLogger")
    logger.warning(f"Violation Detected: {message}")
