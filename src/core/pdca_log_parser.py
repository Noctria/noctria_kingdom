#!/usr/bin/env python3
# coding: utf-8

"""
📦 core/pdca_log_parser.py
- PDCA再評価ログ（veritas_eval_*.json）を集計・統計処理するユーティリティ
- GUIや分析スクリプトから呼び出して再利用可能
"""

from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Optional, Literal, Dict, Any
import json

def parse_date_safe(date_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def load_and_aggregate_pdca_logs(
    log_dir: Path,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    mode: Literal["strategy", "tag"] = "strategy",
    limit: int = 20
) -> Dict[str, Any]:
    """
    再評価ログ（JSON群）を読み取り、改善率・DD改善などを集計
    """
    raw_results = []
    for file in sorted(log_dir.glob("*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            recheck_ts = data.get("recheck_timestamp")
            if not recheck_ts:
                continue

            try:
                ts = datetime.strptime(recheck_ts, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                continue

            if from_date and ts < from_date:
                continue
            if to_date and ts > to_date:
                continue

            win_before = float(data.get("win_rate_before", 0.0))
            win_after = float(data.get("win_rate_after", 0.0))
            dd_before = float(data.get("max_dd_before", 0.0))
            dd_after = float(data.get("max_dd_after", 0.0))

            status = data.get("status") or "unknown"

            raw_results.append({
                "strategy": data.get("strategy"),
                "tag": data.get("tag", "unknown"),
                "win_rate_before": win_before,
                "win_rate_after": win_after,
                "diff": round(win_after - win_before, 2),
                "max_dd_before": dd_before,
                "max_dd_after": dd_after,
                "dd_diff": round(dd_before - dd_after, 2),
                "status": status
            })
        except Exception:
            continue

    group_key = "strategy" if mode == "strategy" else "tag"
    grouped = defaultdict(list)
    for r in raw_results:
        key = r.get(group_key) or "unknown"
        grouped[key].append(r)

    detail_rows = []
    for key, group in grouped.items():
        win_before_vals = [g["win_rate_before"] for g in group]
        win_after_vals = [g["win_rate_after"] for g in group]
        dd_before_vals = [g["max_dd_before"] for g in group]
        dd_after_vals = [g["max_dd_after"] for g in group]

        avg_win_rate_before = sum(win_before_vals) / len(group)
        avg_win_rate_after = sum(win_after_vals) / len(group)
        avg_diff = round(avg_win_rate_after - avg_win_rate_before, 2)

        avg_dd_before = sum(dd_before_vals) / len(group)
        avg_dd_after = sum(dd_after_vals) / len(group)
        dd_diff = round(avg_dd_before - avg_dd_after, 2)

        adopted = any(g["status"] == "adopted" for g in group)

        detail_rows.append({
            "strategy": key,
            "win_rate_before": round(avg_win_rate_before, 2),
            "win_rate_after": round(avg_win_rate_after, 2),
            "diff": avg_diff,
            "max_dd_before": round(avg_dd_before, 2),
            "max_dd_after": round(avg_dd_after, 2),
            "status": "adopted" if adopted else "pending",
        })

    detail_rows.sort(key=lambda x: x["diff"], reverse=True)
    limited_rows = detail_rows[:limit]

    chart_labels = [r["strategy"] for r in limited_rows]
    chart_data = [r["diff"] for r in limited_rows]
    chart_dd_data = [
        round(r["max_dd_before"] - r["max_dd_after"], 2)
        for r in limited_rows
    ]

    all_diffs = [r["diff"] for r in raw_results]
    all_dd_diffs = [r["dd_diff"] for r in raw_results]

    stats = {
        "avg_win_rate_diff": round(sum(all_diffs) / len(all_diffs), 2) if all_diffs else 0.0,
        "avg_dd_diff": round(sum(all_dd_diffs) / len(all_dd_diffs), 2) if all_dd_diffs else 0.0,
        "win_rate_improved": sum(1 for r in raw_results if r["diff"] > 0),
        "dd_improved": sum(1 for r in raw_results if r["dd_diff"] > 0),
        "adopted": sum(1 for r in raw_results if r["status"] == "adopted"),
        "detail": limited_rows,
    }

    return {
        "stats": stats,
        "chart": {
            "labels": chart_labels,
            "data": chart_data,
            "dd_data": chart_dd_data,
        }
    }
