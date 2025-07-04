import datetime
import json
import logging
from typing import Any, Dict


def format_date() -> str:
    """現在の日付と時間を YYYY-MM-DD HH:MM:SS 形式で返す"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_to_json(data: Dict[str, Any], filename: str = "output.json") -> None:
    """辞書型データをJSON形式で保存する"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_json(filename: str = "output.json") -> Dict[str, Any]:
    """JSONファイルを読み込んで辞書として返す"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ JSON読み込み失敗: {e}")
        return {}


def setup_logger(name: str = __name__) -> logging.Logger:
    """名前付きロガーをセットアップして返す（重複ハンドラ防止）"""
    logger = logging.getLogger(name)
    logger.propagate = False  # 重複ログ防止

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


# ✅ 簡単なユーティリティ関数のテスト
if __name__ == "__main__":
    logger = setup_logger("TestLogger")

    sample_data = {
        "strategy": "Aurus_Singularis",
        "decision": "BUY",
        "timestamp": format_date()
    }

    save_to_json(sample_data)
    loaded_data = load_json()

    print("✅ Loaded Data:", loaded_data)
    print("🕒 Current Date:", format_date())
    logger.info("✅ Logger test message complete")
