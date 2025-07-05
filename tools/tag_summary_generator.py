#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas戦略 タグ別統計集計スクリプト
- strategies/veritas_generated/ 内の戦略ログを走査し、
  タグごとの平均勝率・平均取引数・最大DDなどを算出
"""

import json
from pathlib import Path
from collections import defaultdict
from statistics import mean
from core.path_config import STRATEGIES_DIR

# 対象ディレクトリ
GENERATED_DIR = STRATEGIES_DIR / "veritas_generated"

def load_strategy_logs():
    logs = []
    for file in GENERATED_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logs.append(data)
        except Exception as e:
            print(f"⚠️ 読み込み失敗: {file.name} - {e}")
    return logs

def summarize_by_tag(logs):
    tag_summary = defaultdict(lambda: {
        "count": 0,
        "win_rates": [],
        "trade_counts": [],
        "max_drawdowns": [],
        "strategy_names": [],
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
                tag_data["strategy_names"].append(name)

    return tag_summary

def display_summary(tag_summary):
    print("📊 タグ別統計概要")
    print("-" * 50)
    for tag, stats in tag_summary.items():
        print(f"🗂 タグ: {tag}")
        print(f"  - 戦略数: {stats['count']}")
        print(f"  - 平均勝率: {mean(stats['win_rates']):.2f}%")
        print(f"  - 平均取引数: {mean(stats['trade_counts']):.1f}")
        print(f"  - 平均最大DD: {mean(stats['max_drawdowns']):.2f}")
        print(f"  - 戦略例: {', '.join(stats['strategy_names'][:3])}")
        print()

def export_summary_to_json(tag_summary, output_path: Path):
    export_data = {}
    for tag, stats in tag_summary.items():
        export_data[tag] = {
            "strategy_count": stats["count"],
            "average_win_rate": round(mean(stats["win_rates"]), 2),
            "average_trade_count": round(mean(stats["trade_counts"]), 1),
            "average_max_drawdown": round(mean(stats["max_drawdowns"]), 2),
            "sample_strategies": stats["strategy_names"][:5]
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON出力完了: {output_path}")

if __name__ == "__main__":
    logs = load_strategy_logs()
    tag_summary = summarize_by_tag(logs)
    display_summary(tag_summary)

    # JSON保存（任意）
    output_file = GENERATED_DIR / "tag_summary.json"
    export_summary_to_json(tag_summary, output_file)
