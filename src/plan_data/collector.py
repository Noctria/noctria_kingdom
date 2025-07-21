# src/plan_data/collector.py

import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    yf = None

class PlanDataCollector:
    """
    PDCA-Plan策定用 各種ログ・評価・市場データ・外部経済データの統合収集クラス
    """

    def __init__(self, base_dir: Optional[str] = None, fred_api_key: Optional[str] = None):
        self.base_dir = Path(base_dir or "data")
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")

    def collect_act_logs(self) -> List[Dict[str, Any]]:
        # ... 省略（現状コードと同じ）

        # [中略] 既存collect_act_logs/collect_eval_results/collect_market_dataはそのまま使える

    # ▼▼▼ API直接取得：yfinanceの例 ▼▼▼
    def fetch_yfinance_data(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        if yf is None:
            print("[collector] yfinance未インストール")
            return pd.DataFrame()
        df = yf.download(symbol, start=start, end=end, interval=interval)
        if df.empty:
            print("[collector] yfinanceデータなし")
            return pd.DataFrame()
        df = df.reset_index()
        df.rename(columns={"Date": "date"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"])
        return df

    # ▼▼▼ FREDデータ直接取得 ▼▼▼
    def fetch_fred_data(self, series_id: str, start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame:
        if not self.fred_api_key:
            print("[collector] FRED_API_KEY未設定")
            return pd.DataFrame()
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.fred_api_key,
            "file_type": "json",
            "observation_start": start_date,
            "observation_end": end_date,
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            obs = r.json()["observations"]
            df = pd.DataFrame(obs)
            df = df.rename(columns={"date": "fred_date", "value": series_id})
            df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
            df["fred_date"] = pd.to_datetime(df["fred_date"])
            return df[["fred_date", series_id]]
        except Exception as e:
            print(f"[collector] FREDデータ取得失敗: {e}")
            return pd.DataFrame()

    # ▼▼▼ データ統合（例） ▼▼▼
    def collect_all(self, yf_symbol: Optional[str] = None, fred_series: Optional[List[str]] = None) -> pd.DataFrame:
        """
        yfinance, FRED, ログ類のデータを統合したマスターDFを返す
        """
        # 1. yfinance
        start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = datetime.today().strftime("%Y-%m-%d")
        if yf_symbol:
            market_df = self.fetch_yfinance_data(yf_symbol, start=start_date, end=end_date)
        else:
            market_df = pd.DataFrame()

        # 2. FRED
        if fred_series and len(market_df) > 0:
            for sid in fred_series:
                fred_df = self.fetch_fred_data(sid, start_date, end_date)
                if not fred_df.empty:
                    fred_df = fred_df.set_index("fred_date")
                    # 直近値をforward fill
                    market_df[sid] = fred_df[sid].reindex(market_df["date"], method="ffill").values

        # 3. ローカルJSONデータ（例: act_logs, eval_results）は別途メソッドで
        # 必要に応じてmarket_dfにマージ（例: 戦略ログとの日付マージなど）

        # 4. 追加特徴量
        if not market_df.empty:
            market_df["volatility"] = (market_df["High"] - market_df["Low"]) / market_df["Close"]

        return market_df

# スクリプト直接実行テスト
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    collector = PlanDataCollector()
    df = collector.collect_all(yf_symbol="SPY", fred_series=["UNRATE", "FEDFUNDS"])
    print(df.tail())
