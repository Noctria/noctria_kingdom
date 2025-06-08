import datetime
import json
import logging

def format_date():
    """現在の日付と時間を適切な形式で出力"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def save_to_json(data, filename="output.json"):
    """データをJSON形式で保存"""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def load_json(filename="output.json"):
    """JSONファイルを読み込む"""
    with open(filename, "r") as f:
        return json.load(f)

def setup_logger(name=__name__):
    """シンプルなロガー設定"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

# ✅ ユーティリティ関数のテスト
if __name__ == "__main__":
    sample_data = {"strategy": "Aurus_Singularis", "decision": "BUY"}
    save_to_json(sample_data)
    loaded_data = load_json()
    print("Loaded Data:", loaded_data)
    print("Current Date:", format_date())

    # ✅ setup_loggerのテスト
    logger = setup_logger("TestLogger")
    logger.info("Logger test message")
