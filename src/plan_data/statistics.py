# src/plan_data/statistics.py

"""
PDCA-Plan用 統計・KPI算出モジュール
- collector.pyで集約したデータを集計し、主要な統計情報・傾向分析を提供
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from statistics import mean
from src.plan_data.collector import PlanDataCollector

class PlanStatistics:
    def __init__(self, collector: Optional[PlanDataCollector] = None):
        self.collector = collector or PlanDataCollector()
        self._data = self.collector.collect_all()

    def win_rate_stats(self) -> Dict[str, Any]:
        """評価ログから勝率の基本統計を算出"""
        evals = self._data["eval_results"]
        if not evals:
            return {"count": 0, "mean": None, "min": None, "max": None}
        rates = [e.get("win_rate", 0.0) for e in evals if "win_rate" in e]
        return {
            "count": len(rates),
            "mean": round(mean(rates), 2) if rates else None,
            "min": round(min(rates), 2) if rates else None,
            "max": round(max(rates), 2) if rates else None,
        }

    def drawdown_stats(self) -> Dict[str, Any]:
        """評価ログから最大ドローダウンの基本統計を算出"""
        evals = self._data["eval_results"]
        if not evals:
            return {"count": 0, "mean": None, "min": None, "max": None}
        dd = [e.get("max_drawdown", 0.0) for e in evals if "max_drawdown" in e]
        return {
            "count": len(dd),
            "mean": round(mean(dd), 2) if dd else None,
            "min": round(min(dd), 2) if dd else None,
            "max": round(max(dd), 2) if dd else None,
        }

    def tag_performance(self) -> Dict[str, Dict[str, Any]]:
        """タグ別の勝率・採用率などを集計"""
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

    def adoption_rate(self) -> float:
        """評価済み戦略のうち実際にAct採用された割合"""
        evals = self._data["eval_results"]
        if not evals:
            return 0.0
        adopted = [e for e in evals if e.get("pushed") is True]
        return round(100 * len(adopted) / len(evals), 2)

    def act_signal_stats(self) -> Dict[str, int]:
        """ActログにおけるBUY/SELLの回数などを集計"""
        logs = self._data["act_logs"]
        counter = Counter(log.get("signal", "UNKNOWN") for log in logs)
        return dict(counter)

    def get_summary(self) -> Dict[str, Any]:
        """PDCA-Planで使うサマリー統計セットをまとめて返す"""
        return {
            "win_rate_stats": self.win_rate_stats(),
            "drawdown_stats": self.drawdown_stats(),
            "adoption_rate": self.adoption_rate(),
            "tag_performance": self.tag_performance(),
            "act_signal_stats": self.act_signal_stats(),
        }


# テスト/手動実行用
if __name__ == "__main__":
    stats = PlanStatistics()
    summary = stats.get_summary()
    import json
    print(json.dumps(summary, indent=2, ensure_ascii=False))
