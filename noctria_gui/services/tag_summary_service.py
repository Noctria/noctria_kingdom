#!/usr/bin/env python3
# coding: utf-8

"""
🧠 タグ別戦略統計サービス
- veritas_generated 戦略ログを読み込み、タグ別統計を集計
"""

import json
from collections import defaultdict
from statistics import mean
from pathlib import Path
from typing import List, Dict

from src.core.path_config import STRATEGIES_DIR


def load_all_statistics() -> List[Dict]:
    """
    📦 veritas_generated ディレクトリから全戦略の統計ログを取得
    """
    generated_dir = STRATEGIES_DIR / "veritas_generated"
    logs = []

    for file in generated_dir.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                logs.append(json.load(f))
        except Exception as e:
            print(f"⚠️ 読み込み失敗: {file.name} - {e}")
    return logs


def summarize_by_tag(logs: List[Dict]) -> List[Dict]:
    """
    🧠 タグごとに統計情報を集計
    """
    tag_summary = defaultdict(lambda: {
        "count": 0,
        "win_rates": [],
        "trade_counts": [],
        "max_drawdowns": [],
        "strategy_names": set(),
    })

    for log in logs:
        tags = log.get("tags", [])
        if not isinstance(tags, list):
            continue

        win_rate = log.get("win_rate")
        trade_count = log.get("num_trades")
        max_dd = log.get("max_drawdown")
        name = log.get("strategy")

        for tag in tags:
            tag_data = tag_summary[tag]
            tag_data["count"] += 1
            if win_rate is not None:
                tag_data["win_rates"].append(win_rate)
            if trade_count is not None:
                tag_data["trade_counts"].append(trade_count)
            if max_dd is not None:
                tag_data["max_drawdowns"].append(max_dd)
            if name:
                tag_data["strategy_names"].add(name)

    summary_data = []
    for tag, stats in tag_summary.items():
        summary_data.append({
            "tag": tag,
            "strategy_count": stats["count"],
            "average_win_rate": round(mean(stats["win_rates"]), 2) if stats["win_rates"] else 0.0,
            "average_trade_count": round(mean(stats["trade_counts"]), 1) if stats["trade_counts"] else 0.0,
            "average_max_drawdown": round(mean(stats["max_drawdowns"]), 2) if stats["max_drawdowns"] else 0.0,
            "sample_strategies": sorted(list(stats["strategy_names"]))[:5]
        })

    # 🧭 表示を戦略数の多い順に並べ替え
    return sorted(summary_data, key=lambda x: x["strategy_count"], reverse=True)
