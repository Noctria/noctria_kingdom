# src/plan_data/statistics.py
from collections import defaultdict

def summarize_win_rate(eval_results):
    """勝率の平均・中央値などを計算"""
    rates = [r.get("win_rate") for r in eval_results if "win_rate" in r]
    if not rates:
        return {"mean": 0, "median": 0}
    rates_sorted = sorted(rates)
    n = len(rates)
    mean = sum(rates) / n
    median = rates_sorted[n//2] if n % 2 else (rates_sorted[n//2-1] + rates_sorted[n//2]) / 2
    return {"mean": mean, "median": median}

def tagwise_stats(eval_results):
    """タグごとの集計"""
    tag_stats = defaultdict(list)
    for r in eval_results:
        tags = r.get("tags", [])
        for t in tags:
            tag_stats[t].append(r)
    # タグごとの平均勝率/最大DDを返す
    return {
        tag: {
            "avg_win_rate": sum(x.get("win_rate", 0) for x in lst)/len(lst),
            "avg_drawdown": sum(x.get("max_drawdown", 0) for x in lst)/len(lst),
            "count": len(lst)
        }
        for tag, lst in tag_stats.items()
    }

