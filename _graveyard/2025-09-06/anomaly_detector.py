# src/plan_data/anomaly_detector.py

import pandas as pd
from typing import List, Dict, Any, Optional

# --- 評価ログ(dict)ベースの異常検知 ---

def detect_drawdown_anomalies(eval_results: List[Dict], dd_threshold: float = 20.0) -> List[Dict]:
    """最大DDが異常値の戦略を検出（単体戦略 or 評価ログdict）"""
    return [r for r in eval_results if r.get("max_drawdown", 0) > dd_threshold]

def detect_low_win_rate(eval_results: List[Dict], rate_threshold: float = 40.0) -> List[Dict]:
    """勝率が著しく低い戦略を検出"""
    return [r for r in eval_results if r.get("win_rate", 100) < rate_threshold]

def detect_extreme_trades(eval_results: List[Dict], max_trades: int = 500) -> List[Dict]:
    """取引数が異常に多い（過剰最適化・リスク）の戦略"""
    return [r for r in eval_results if r.get("num_trades", 0) > max_trades]

# --- DataFrame（時系列）ベースの異常検知 ---

def detect_timeseries_anomalies(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    z_thresh: float = 3.0,
) -> Dict[str, pd.DataFrame]:
    """
    指定カラムでzスコア異常値を検出（ニュース件数・マクロ等にも使える）
    """
    result = {}
    if columns is None:
        # デフォルトは、ニュース/マクロ/ボラ/勝率等を自動検出
        columns = [c for c in df.columns if any(w in c.lower() for w in ["win_rate", "drawdown", "dd", "news", "cpi", "volatility", "spike"])]
    for col in columns:
        if col not in df.columns:
            continue
        s = df[col]
        mu, std = s.mean(), s.std()
        zscore = (s - mu) / (std + 1e-9)
        anomalies = df[(zscore.abs() > z_thresh)]
        if not anomalies.empty:
            result[col] = anomalies
    return result

def detect_event_shock_days(df: pd.DataFrame, event_col: str, target_col: str, thresh: float = 2.0) -> pd.DataFrame:
    """
    主要イベント（FOMC等）で、勝率・ボラ等に異常（直近平均比2倍超等）が発生した日を抽出
    """
    if event_col not in df.columns or target_col not in df.columns:
        return pd.DataFrame()
    ev_days = df[df[event_col] == 1]
    mean = df[target_col].rolling(20).mean()
    std = df[target_col].rolling(20).std()
    anomaly_days = ev_days[(ev_days[target_col] > mean + std * thresh) | (ev_days[target_col] < mean - std * thresh)]
    return anomaly_days

# --- 異常要約のラッパー ---

def summarize_anomalies(eval_results: List[Dict], df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    検出異常をまとめて要約
    """
    result = {
        "high_dd": detect_drawdown_anomalies(eval_results),
        "low_win_rate": detect_low_win_rate(eval_results),
        "extreme_trades": detect_extreme_trades(eval_results),
    }
    if df is not None and isinstance(df, pd.DataFrame):
        result["timeseries_anomalies"] = detect_timeseries_anomalies(df)
        # 例: FOMCイベント×勝率異常
        for ev in ["FOMC", "CPI", "NFP"]:
            if ev in df.columns and "win_rate" in df.columns:
                result[f"{ev}_shock_days"] = detect_event_shock_days(df, ev, "win_rate")
    return result

# --- テスト用 ---
if __name__ == "__main__":
    # 例: 評価ログdict（ダミー）
    eval_results = [
        {"strategy": "A", "max_drawdown": 30, "win_rate": 35, "num_trades": 600},
        {"strategy": "B", "max_drawdown": 10, "win_rate": 75, "num_trades": 50},
        {"strategy": "C", "max_drawdown": 5, "win_rate": 22, "num_trades": 120},
    ]
    print("■DD異常:", detect_drawdown_anomalies(eval_results))
    print("■勝率低:", detect_low_win_rate(eval_results))
    print("■取引多:", detect_extreme_trades(eval_results))

    # 例: DataFrameベース
    import pandas as pd
    import numpy as np
    df = pd.DataFrame({
        "Date": pd.date_range("2023-01-01", periods=100),
        "win_rate": np.random.normal(60, 10, 100),
        "News_Count": np.random.poisson(15, 100),
        "FOMC": [1 if i % 30 == 0 else 0 for i in range(100)]
    })
    # 極端値を混ぜる
    df.loc[10, "win_rate"] = 10
    df.loc[50, "News_Count"] = 60
    print("■時系列異常:", detect_timeseries_anomalies(df))
    print("■FOMCショック日:", detect_event_shock_days(df, "FOMC", "win_rate"))
