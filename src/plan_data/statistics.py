"""
PDCA-Plan用 統計・KPI算出モジュール
- collector.pyで集約した時系列データや評価ログを多角的に集計
- 主要な統計情報・傾向分析・ニュース件数・マクロ・タグ分析にも対応
"""

from typing import Dict, Any, List, Optional, Union
from collections import defaultdict, Counter
from statistics import mean, stdev
import pandas as pd
from src.plan_data.collector import PlanDataCollector, ASSET_SYMBOLS

class PlanStatistics:
    def __init__(self, collector: Optional[PlanDataCollector] = None, use_timeseries: bool = True, lookback_days: int = 365):
        self.collector = collector or PlanDataCollector()
        # データ型によって使い分け
        self._data = self.collector.collect_all(lookback_days=lookback_days)
        self._is_timeseries = isinstance(self._data, pd.DataFrame) and "Date" in self._data.columns

    # --- 評価ログ・戦略系（従来互換） ---
    def win_rate_stats(self) -> Dict[str, Any]:
        """評価ログから勝率の基本統計を算出"""
        # ①評価ログ形式
        if isinstance(self._data, dict) and "eval_results" in self._data:
            evals = self._data["eval_results"]
            if not evals:
                return {"count": 0, "mean": None, "min": None, "max": None}
            rates = [e.get("win_rate", 0.0) for e in evals if "win_rate" in e]
        # ②時系列DF形式
        elif self._is_timeseries and "win_rate" in self._data.columns:
            rates = self._data["win_rate"].dropna().tolist()
        else:
            rates = []
        return {
            "count": len(rates),
            "mean": round(mean(rates), 2) if rates else None,
            "min": round(min(rates), 2) if rates else None,
            "max": round(max(rates), 2) if rates else None,
            "std": round(stdev(rates), 2) if len(rates) > 1 else None
        }

    def drawdown_stats(self) -> Dict[str, Any]:
        """評価ログまたはDFから最大ドローダウンの基本統計を算出"""
        if isinstance(self._data, dict) and "eval_results" in self._data:
            evals = self._data["eval_results"]
            dd = [e.get("max_drawdown", 0.0) for e in evals if "max_drawdown" in e]
        elif self._is_timeseries and "max_dd" in self._data.columns:
            dd = self._data["max_dd"].dropna().tolist()
        else:
            dd = []
        return {
            "count": len(dd),
            "mean": round(mean(dd), 2) if dd else None,
            "min": round(min(dd), 2) if dd else None,
            "max": round(max(dd), 2) if dd else None,
            "std": round(stdev(dd), 2) if len(dd) > 1 else None
        }

    def tag_performance(self) -> Dict[str, Dict[str, Any]]:
        """タグ別の勝率・採用率などを集計"""
        if isinstance(self._data, dict) and "eval_results" in self._data:
            evals = self._data["eval_results"]
            tag_stats = defaultdict(list)
            for e in evals:
                tags = e.get("tags", [])
                for tag in tags:
                    tag_stats[tag].append(e)
            result = {}
            for tag, lst in tag_stats.items():
                win_rates = [x.get("win_rate", 0.0) for x in lst]
                result[tag] = {
                    "count": len(lst),
                    "mean_win_rate": round(mean(win_rates), 2) if win_rates else None,
                }
            return result
        # 時系列DF形式でtagカラムがある場合
        elif self._is_timeseries and "tag" in self._data.columns:
            df = self._data
            tag_stats = df.groupby("tag")["win_rate"].agg(["count", "mean", "std"]).reset_index()
            return tag_stats.to_dict(orient="records")
        else:
            return {}

    def adoption_rate(self) -> float:
        """評価済み戦略のうちAct採用割合"""
        if isinstance(self._data, dict) and "eval_results" in self._data:
            evals = self._data["eval_results"]
            if not evals:
                return 0.0
            adopted = [e for e in evals if e.get("pushed") is True]
            return round(100 * len(adopted) / len(evals), 2)
        # 時系列型には非対応（None）
        return None

    def act_signal_stats(self) -> Dict[str, int]:
        """ActログにおけるBUY/SELLの回数などを集計"""
        if isinstance(self._data, dict) and "act_logs" in self._data:
            logs = self._data["act_logs"]
            counter = Counter(log.get("signal", "UNKNOWN") for log in logs)
            return dict(counter)
        # 時系列型には非対応（None）
        return {}

    # --- 時系列/マクロ/ニュース・イベント系 ---
    def macro_stats(self) -> Dict[str, Any]:
        """マクロ経済指標（FRED, CPI, etc）ごとの統計量"""
        result = {}
        if self._is_timeseries:
            for col in self._data.columns:
                if col.endswith("_Value"):
                    s = self._data[col].dropna()
                    result[col] = {
                        "mean": s.mean(),
                        "std": s.std(),
                        "min": s.min(),
                        "max": s.max(),
                    }
        return result

    def news_stats(self) -> Dict[str, Any]:
        """NewsAPI等によるニュース件数やポジ/ネガ件数の統計"""
        stats = {}
        if self._is_timeseries and "News_Count" in self._data.columns:
            nc = self._data["News_Count"].dropna()
            stats["News_Count"] = {
                "mean": int(nc.mean()),
                "std": int(nc.std()),
                "min": int(nc.min()),
                "max": int(nc.max()),
            }
        if self._is_timeseries and "News_Positive" in self._data.columns:
            np_ = self._data["News_Positive"].dropna()
            stats["News_Positive"] = {
                "mean": int(np_.mean()),
                "std": int(np_.std()),
                "min": int(np_.min()),
                "max": int(np_.max()),
            }
        if self._is_timeseries and "News_Negative" in self._data.columns:
            nn = self._data["News_Negative"].dropna()
            stats["News_Negative"] = {
                "mean": int(nn.mean()),
                "std": int(nn.std()),
                "min": int(nn.min()),
                "max": int(nn.max()),
            }
        return stats

    def event_stats(self) -> Dict[str, Any]:
        """主要イベント（FOMC等）の日数や発生日一覧"""
        result = {}
        if self._is_timeseries:
            for ev in ["FOMC", "CPI", "NFP", "ECB", "BOJ", "GDP"]:
                if ev in self._data.columns:
                    days = self._data[self._data[ev] == 1]["Date"]
                    result[ev] = {
                        "count": len(days),
                        "recent": days.max() if not days.empty else None
                    }
        return result

    def get_summary(self) -> Dict[str, Any]:
        """PDCA-Planで使うサマリー統計セットをまとめて返す（複合データ対応）"""
        return {
            "win_rate_stats": self.win_rate_stats(),
            "drawdown_stats": self.drawdown_stats(),
            "adoption_rate": self.adoption_rate(),
            "tag_performance": self.tag_performance(),
            "act_signal_stats": self.act_signal_stats(),
            "macro_stats": self.macro_stats(),
            "news_stats": self.news_stats(),
            "event_stats": self.event_stats(),
        }


# テスト/手動実行用
if __name__ == "__main__":
    stats = PlanStatistics()
    summary = stats.get_summary()
    import json
    print(json.dumps(summary, indent=2, ensure_ascii=False))
