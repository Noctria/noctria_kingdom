# core/settings.py

import os
from dotenv import load_dotenv

# .env を読み込む
load_dotenv()

# Alpha Vantage 用 APIキーを取得
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")

# FRED APIキーを取得（環境変数が設定されていなければ空文字）
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# 追加の設定があればここに追記可能
# 例: デバッグフラグやログレベルなど
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# ロギング設定に連動させるなど、環境変数を活用しやすくするためのフラグを準備
