# src/plan_data/statistics.py
"""
PDCA-Plan用 統計・KPI算出モジュール
- collector.py で集約した時系列データや評価ログを多角的に集計
- 主要な統計情報（win_rate / drawdown / Sharpe / trades など）とニュース・マクロ・イベント集計
- 特徴量DFに KPI 列を付与するユーティリティ（attach_kpis）も提供
"""

from __future__ import annotations

import math
import time
from typing import Dict, Any, List, Optional, Union
from collections import defaultdict, Counter
from statistics import mean, stdev

import numpy as np
import pandas as pd

# ---- imports（相対/絶対の両対応） ----
try:
    from plan_data.collector import PlanDataCollector, ASSET_SYMBOLS  # type: ignore
    from plan_data.feature_spec import FEATURE_SPEC  # 互換のため残置（本ファイル内では未使用）  # type: ignore
    from plan_data.observability import log_plan_run  # type: ignore
    from plan_data.trace import new_trace_id  # type: ignore
except Exception:  # 実行環境により src. 付きでの実行も許容
    from src.plan_data.collector import PlanDataCollector, ASSET_SYMBOLS  # type: ignore
    from src.plan_data.feature_spec import FEATURE_SPEC  # type: ignore
    from src.plan_data.observability import log_plan_run  # type: ignore
    from src.plan_data.trace import new_trace_id  # type: ignore


# =========================
# 内部ユーティリティ
# =========================
def _missing_ratio(df: Optional[pd.DataFrame]) -> float:
    """全体欠損率（'date' は除外）。空なら 1.0。"""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return 1.0
    cols = [c for c in df.columns if c != "date"]
    if not cols:
        return 0.0
    total = len(df) * len(cols)
    if total <= 0:
        return 0.0
    return float(df[cols].isna().sum().sum()) / float(total)


def _rows_count(data: Union[pd.DataFrame, dict, None]) -> int:
    if isinstance(data, pd.DataFrame):
        return len(data)
    if isinstance(data, dict):
        if "eval_results" in data and isinstance(data["eval_results"], list):
            return len(data["eval_results"])
        if "act_logs" in data and isinstance(data["act_logs"], list):
            return len(data["act_logs"])
    return 0


def _pick_primary_close(df: pd.DataFrame) -> Optional[str]:
    """代表価格列候補を選ぶ。優先: usdjpy_close → sp500_close → vix_close → 最初の *_close"""
    prefs = ["usdjpy_close", "sp500_close", "vix_close"]
    for p in prefs:
        if p in df.columns:
            return p
    for c in df.columns:
        if isinstance(c, str) and c.endswith("_close"):
            return c
    return None


def _rolling_sharpe(
    ret: pd.Series,
    window: int = 30,
    annualizer: float = math.sqrt(252),
) -> pd.Series:
    r = pd.to_numeric(ret, errors="coerce")
    mu = r.rolling(window=window, min_periods=max(5, window // 3)).mean()
    sd = r.rolling(window=window, min_periods=max(5, window // 3)).std()
    sharpe = (mu / sd.replace(0.0, np.nan)) * annualizer
    return sharpe


def _rolling_max_drawdown(prices: pd.Series, window: int = 180) -> pd.Series:
    """価格系列に対して、各時点で過去 window の最大ドローダウン（負値）を返す。"""
    p = pd.to_numeric(prices, errors="coerce")
    roll = p.rolling(window=window, min_periods=max(5, window // 6))

    def _dd(s: pd.Series) -> float:
        if s.isna().all():
            return np.nan
        peak = s.cummax()
        dd = (s / peak) - 1.0
        return float(dd.min())

    return roll.apply(_dd, raw=False)


# =========================
# KPI 付与ユーティリティ
# =========================
def attach_kpis(
    df: pd.DataFrame,
    *,
    primary_close_col: Optional[str] = None,
    win_window: int = 30,
    dd_window: int = 180,
    sharpe_window: int = 30,
    trace_id: Optional[str] = None,
) -> pd.DataFrame:
    """
    入力: features.py 後の DF（date 昇順・snake_case想定）
    出力: KPI列（win_rate, max_dd, num_trades, sharpe_30d, kpi_ret）を結合した DF
    ついでに phase="statistics" を obs_plan_runs に記録。
    """
    t0 = time.time()
    trace_id = trace_id or new_trace_id(symbol="MULTI", timeframe="1d")

    out = df.copy()
    if "date" in out.columns:
        out = out.sort_values("date").reset_index(drop=True)

    ccol = primary_close_col or _pick_primary_close(out)
    if not ccol or ccol not in out.columns:
        # KPIは付与せずログだけ流して返す
        try:
            log_plan_run(
                None,
                phase="statistics",
                rows=len(out),
                dur_sec=int(time.time() - t0),
                missing_ratio=_missing_ratio(out),
                error_rate=1.0,  # 代表列見つからず
                trace_id=trace_id,
            )
        except Exception:
            pass
        return out

    # 日次リターン
    price = pd.to_numeric(out[ccol], errors="coerce")
    ret = price.pct_change(fill_method=None)
    out["kpi_ret"] = ret

    # win_rate（rolling）
    wins = (ret > 0).astype("float")
    out["win_rate"] = wins.rolling(window=win_window, min_periods=max(5, win_window // 3)).mean() * 100.0

    # num_trades（rollingでの“有意な変化”回数っぽい proxy）
    eps = ret.abs().rolling(window=5, min_periods=3).std() * 0.1
    active = (ret.abs() > eps.fillna(0))
    out["num_trades"] = active.rolling(window=win_window, min_periods=max(5, win_window // 3)).sum()

    # sharpe（rolling）
    out["sharpe_30d"] = _rolling_sharpe(ret, window=sharpe_window)

    # max drawdown（rolling）
    out["max_dd"] = _rolling_max_drawdown(price, window=dd_window)

    # 観測ログ
    try:
        log_plan_run(
            None,
            phase="statistics",
            rows=len(out),
            dur_sec=int(time.time() - t0),
            missing_ratio=_missing_ratio(out),
            error_rate=0.0,
            trace_id=trace_id,
        )
    except Exception:
        pass

    return out


# =========================
# サマリ統計クラス（後方互換）
# =========================
class PlanStatistics:
    def __init__(
        self,
        collector: Optional[PlanDataCollector] = None,
        use_timeseries: bool = True,
        lookback_days: int = 365,
        trace_id: Optional[str] = None,
        df: Optional[pd.DataFrame] = None,  # 追加: 既存DFを直接渡せる
    ):
        """
        df を明示指定しない場合は collector.collect_all(...) を実行して取得。
        """
        self.collector = collector or PlanDataCollector()
        self._data = df if isinstance(df, pd.DataFrame) else self.collector.collect_all(lookback_days=lookback_days)

        # カラム名を安全に小文字へ
        if isinstance(self._data, pd.DataFrame):
            self._data.columns = [str(c).lower() for c in self._data.columns]

        self._is_timeseries = isinstance(self._data, pd.DataFrame) and "date" in self._data.columns
        self._trace_id = trace_id or new_trace_id(symbol="MULTI", timeframe="1d")

        # 代表 KPI を内部にも付与しておく（存在時のみ）
        if self._is_timeseries:
            try:
                self._data = attach_kpis(self._data, trace_id=self._trace_id)
            except Exception:
                # KPI 付与失敗時も summary は続行可能
                pass

    # --- 評価ログ・戦略系（互換） ---
    def win_rate_stats(self) -> Dict[str, Any]:
        """
        勝率の基本統計
        優先順: DFの 'win_rate' 列（%）→ 評価ログ 'win_rate' → DF の binary 'win_flag'
        """
        # DF の win_rate（rolling %）を優先
        if self._is_timeseries and "win_rate" in self._data.columns:
            vals = pd.to_numeric(self._data["win_rate"], errors="coerce").dropna().tolist()
            return {
                "count": len(vals),
                "mean": round(mean(vals), 2) if vals else None,
                "min": round(min(vals), 2) if vals else None,
                "max": round(max(vals), 2) if vals else None,
                "std": round(stdev(vals), 2) if len(vals) > 1 else None,
            }

        # 従来の評価ログ
        if isinstance(self._data, dict) and "eval_results" in self._data:
            evals = self._data["eval_results"]
            rates = [e.get("win_rate", 0.0) for e in evals if "win_rate" in e]
            return {
                "count": len(rates),
                "mean": round(mean(rates), 2) if rates else None,
                "min": round(min(rates), 2) if rates else None,
                "max": round(max(rates), 2) if rates else None,
                "std": round(stdev(rates), 2) if len(rates) > 1 else None,
            }

        # binary フラグ
        if self._is_timeseries and "win_flag" in self._data.columns:
            vals = pd.to_numeric(self._data["win_flag"], errors="coerce").dropna().tolist()
            return {
                "count": len(vals),
                "mean": round(mean(vals), 2) if vals else None,
                "min": round(min(vals), 2) if vals else None,
                "max": round(max(vals), 2) if vals else None,
                "std": round(stdev(vals), 2) if len(vals) > 1 else None,
            }

        return {"count": 0, "mean": None, "min": None, "max": None, "std": None}

    def drawdown_stats(self) -> Dict[str, Any]:
        """
        最大ドローダウンの基本統計
        優先順: DF の 'max_dd'（rolling）→ 'drawdown' → 評価ログの 'drawdown'
        """
        # DF の max_dd を優先
        if self._is_timeseries and "max_dd" in self._data.columns:
            dd = pd.to_numeric(self._data["max_dd"], errors="coerce").dropna().tolist()
        elif self._is_timeseries and "drawdown" in self._data.columns:
            dd = pd.to_numeric(self._data["drawdown"], errors="coerce").dropna().tolist()
        elif isinstance(self._data, dict) and "eval_results" in self._data:
            evals = self._data["eval_results"]
            dd = [e.get("drawdown", 0.0) for e in evals if "drawdown" in e]
        else:
            dd = []

        return {
            "count": len(dd),
            "mean": round(mean(dd), 2) if dd else None,
            "min": round(min(dd), 2) if dd else None,
            "max": round(max(dd), 2) if dd else None,
            "std": round(stdev(dd), 2) if len(dd) > 1 else None,
        }

    def tag_performance(self) -> Union[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """タグ別の勝率・採用率などを集計（評価ログ or DFの tag/win_flag）"""
        if isinstance(self._data, dict) and "eval_results" in self._data:
            evals = self._data["eval_results"]
            tag_stats = defaultdict(list)
            for e in evals:
                tags = e.get("tags", []) or []
                for tag in tags:
                    tag_stats[tag].append(e)
            result: Dict[str, Dict[str, Any]] = {}
            for tag, lst in tag_stats.items():
                win_rates = [x.get("win_rate", 0.0) for x in lst if "win_rate" in x]
                result[tag] = {
                    "count": len(lst),
                    "mean_win_rate": round(mean(win_rates), 2) if win_rates else None,
                }
            return result

        if self._is_timeseries and ("tag" in self._data.columns) and ("win_flag" in self._data.columns):
            df = self._data
            tag_stats = df.groupby("tag")["win_flag"].agg(["count", "mean", "std"]).reset_index()
            return tag_stats.to_dict(orient="records")

        return {}

    def adoption_rate(self) -> Optional[float]:
        """評価済み戦略のうちAct採用割合（評価ログがある場合のみ）"""
        if isinstance(self._data, dict) and "eval_results" in self._data:
            evals = self._data["eval_results"]
            if not evals:
                return 0.0
            adopted = [e for e in evals if e.get("pushed") is True]
            return round(100 * len(adopted) / len(evals), 2)
        return None

    def act_signal_stats(self) -> Dict[str, int]:
        """ActログにおけるBUY/SELLの回数などを集計（評価ログがある場合のみ）"""
        if isinstance(self._data, dict) and "act_logs" in self._data:
            logs = self._data["act_logs"]
            counter = Counter(log.get("signal", "UNKNOWN") for log in logs)
            return dict(counter)
        return {}

    # --- 時系列/マクロ/ニュース・イベント系 ---
    def macro_stats(self) -> Dict[str, Any]:
        """マクロ経済指標（FRED, CPI, etc）ごとの統計量"""
        result: Dict[str, Any] = {}
        if self._is_timeseries:
            for col in self._data.columns:
                if isinstance(col, str) and col.endswith("_value"):
                    s = pd.to_numeric(self._data[col], errors="coerce").dropna()
                    result[col] = {
                        "mean": float(s.mean()) if not s.empty else None,
                        "std": float(s.std()) if not s.empty else None,
                        "min": float(s.min()) if not s.empty else None,
                        "max": float(s.max()) if not s.empty else None,
                    }
        return result

    def news_stats(self) -> Dict[str, Any]:
        """ニュース件数とポジ/ネガ件数の統計"""
        stats: Dict[str, Any] = {}
        if self._is_timeseries and "news_count" in self._data.columns:
            nc = pd.to_numeric(self._data["news_count"], errors="coerce").dropna()
            stats["news_count"] = {
                "mean": int(nc.mean()) if not nc.empty else 0,
                "std": int(nc.std()) if not nc.empty else 0,
                "min": int(nc.min()) if not nc.empty else 0,
                "max": int(nc.max()) if not nc.empty else 0,
            }
        if self._is_timeseries and "news_positive" in self._data.columns:
            np_ = pd.to_numeric(self._data["news_positive"], errors="coerce").dropna()
            stats["news_positive"] = {
                "mean": int(np_.mean()) if not np_.empty else 0,
                "std": int(np_.std()) if not np_.empty else 0,
                "min": int(np_.min()) if not np_.empty else 0,
                "max": int(np_.max()) if not np_.empty else 0,
            }
        if self._is_timeseries and "news_negative" in self._data.columns:
            nn = pd.to_numeric(self._data["news_negative"], errors="coerce").dropna()
            stats["news_negative"] = {
                "mean": int(nn.mean()) if not nn.empty else 0,
                "std": int(nn.std()) if not nn.empty else 0,
                "min": int(nn.min()) if not nn.empty else 0,
                "max": int(nn.max()) if not nn.empty else 0,
            }
        return stats

    def event_stats(self) -> Dict[str, Any]:
        """主要イベント（fomc等）の日数や発生日一覧"""
        result: Dict[str, Any] = {}
        if self._is_timeseries:
            for ev in ["fomc", "cpi", "nfp", "ecb", "boj", "gdp"]:
                if ev in self._data.columns:
                    days = pd.to_datetime(self._data[pd.to_numeric(self._data[ev], errors="coerce") == 1]["date"], errors="coerce")
                    days = days.dropna()
                    result[ev] = {
                        "count": int(len(days)),
                        "recent": str(days.max()) if not days.empty else None,
                    }
        return result

    def get_summary(self) -> Dict[str, Any]:
        """
        PDCA-Planで使うサマリー統計セットをまとめて返す（複合データ対応）
        ついでに phase="statistics" として観測ログに計測を記録。
        """
        t0 = time.time()

        summary = {
            "win_rate_stats": self.win_rate_stats(),
            "drawdown_stats": self.drawdown_stats(),
            "adoption_rate": self.adoption_rate(),
            "tag_performance": self.tag_performance(),
            "act_signal_stats": self.act_signal_stats(),
            "macro_stats": self.macro_stats(),
            "news_stats": self.news_stats(),
            "event_stats": self.event_stats(),
        }

        # 観測ログ（失敗は握りつぶして継続）
        try:
            log_plan_run(
                None,  # env NOCTRIA_OBS_PG_DSN を使用
                phase="statistics",
                rows=_rows_count(self._data),
                dur_sec=int(time.time() - t0),
                missing_ratio=_missing_ratio(self._data if isinstance(self._data, pd.DataFrame) else None),
                error_rate=0.0,  # TODO: 集計失敗件数などを加味
                trace_id=self._trace_id,
            )
        except Exception:
            pass

        return summary


__all__ = [
    "attach_kpis",
    "PlanStatistics",
]


# テスト/手動実行用
if __name__ == "__main__":
    # 1) 収集→KPI付与→概要統計
    base_df = PlanDataCollector().collect_all(lookback_days=240)
    df_kpi = attach_kpis(base_df)

    stats = PlanStatistics(df=df_kpi)  # 既存DFを渡して再収集を省略
    summary = stats.get_summary()

    import json
    pd.set_option("display.max_columns", 120)
    print("[KPI columns present?]", {"win_rate": "win_rate" in df_kpi.columns, "max_dd": "max_dd" in df_kpi.columns})
    print(json.dumps(summary, indent=2, ensure_ascii=False))
