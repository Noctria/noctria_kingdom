import os
import csv
import logging
from datetime import datetime


def setup_logger(name="System", log_file='logs/system.log', level=logging.INFO):
    """
    共通ロガーセットアップ関数
    """
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 重複Handler防止
    if not logger.handlers:
        fh = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def log_violation(message, log_file='logs/violation.log'):
    """
    ルール違反ログ記録（例：ドローダウン制限など）
    """
    logger = setup_logger(name="ViolationLogger", log_file=log_file, level=logging.WARNING)
    logger.warning(f"Violation Detected: {message}")


def log_strategy_result(strategy_name, input_data, output, log_dir="logs/strategy_performance"):
    """
    各戦略AIの実行ログをCSVで記録
    """
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d')}_{strategy_name}.csv")
    is_new_file = not os.path.exists(log_file)

    with open(log_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(["Timestamp", "Input", "Output"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(input_data),
            str(output)
        ])


def log_final_decision(decision_dict, final_action, log_dir="logs/strategy_performance"):
    """
    Noctria王の統合判断を記録（戦略ごとの出力と最終決定）
    """
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d')}_final_decision.csv")
    is_new_file = not os.path.exists(log_file)

    with open(log_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(["Timestamp", "FinalAction", "Details"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            final_action,
            str(decision_dict)
        ])
