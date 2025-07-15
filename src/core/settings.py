# core/settings.py

import os
from dotenv import load_dotenv

# .env を読み込む
load_dotenv()

# Alpha Vantage 用 APIキーを取得
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

# ✅ この行を追加
FRED_API_KEY = os.getenv("FRED_API_KEY") 
