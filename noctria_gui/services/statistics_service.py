#!/usr/bin/env python3
# coding: utf-8

"""
📊 Veritas戦略ログ統計サービス
- PDCAログから統計情報を抽出・整形する
- 統計ダッシュボード用のデータ提供モジュール
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

from core.path_config import PDCA_LOG_DIR


def load_all_logs() -> List[Dict]:
    """
    📁 PDCAログディレクトリから全ログを読み込む
    """
    logs = []
    for file in sorted(PDCA_LOG_DIR.glob("*.json"), reverse=True):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["__log_path__"] = str(file)
                logs.append(data)
        except Exception as e:
            print(f"⚠️ ログ読み込み失敗: {file.name} - {e}")
    return logs


def filter_logs(
    logs: List[Dict],
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict]:
    """
    🔍 ログにフィルタを適用する
    """
    filtered = []

    for log in logs:
        if strategy and log.get("strategy") != strategy:
            continue
        if symbol and log.get("symbol") != symbol:
            continue
        if start_date or end_date:
            log_ts = log.get("timestamp")
            try:
                dt = datetime.fromisoformat(log_ts)
                if start_date and dt < datetime.fromisoformat(start_date):
                    continue
                if end_date and dt > datetime.fromisoformat(end_date):
                    continue
            except Exception as e:
                print(f"⚠️ 日付解析失敗: {log_ts} - {e}")
                continue
        filtered.append(log)

    return filtered


def sort_logs(logs: List[Dict], sort_key: str, descending: bool = True) -> List[Dict]:
    """
    ↕️ 指定キーでソート（例：win_rate, max_drawdown）
    """
    return sorted(
        logs,
        key=lambda x: x.get(sort_key, 0.0),
        reverse=descending
    )


def get_available_strategies(logs: List[Dict]) -> List[str]:
    """
    🗂 使用された戦略名一覧を返す（重複排除）
    """
    return sorted(set(
        log["strategy"] for log in logs if "strategy" in log and log["strategy"]
    ))


def get_available_symbols(logs: List[Dict]) -> List[str]:
    """
    💱 使用された通貨ペア一覧を返す（重複排除）
    """
    return sorted(set(
        log["symbol"] for log in logs if "symbol" in log and log["symbol"]
    ))


def load_all_statistics() -> List[Dict]:
    """
    📊 統計対象として有効なPDCAログを抽出する
    """
    logs = load_all_logs()
    return [
        log for log in logs
        if all(k in log for k in ("strategy", "symbol", "win_rate", "max_drawdown", "trade_count", "timestamp"))
    ]


def filter_statistics(
    sort_by: str = "win_rate",
    descending: bool = True,
    strategy: Optional[str] = None,
    symbol: Optional[str] = None
) -> List[Dict]:
    """
    🔍 統計データにフィルタ・ソートを適用
    """
    logs = load_all_statistics()
    filtered = filter_logs(logs, strategy=strategy, symbol=symbol)
    return sort_logs(filtered, sort_key=sort_by, descending=descending)


def export_statistics_to_csv(logs: List[Dict], output_path: Path):
    """
    📤 Veritas戦略の統計ログをCSV形式で出力する
    """
    if not logs:
        print("⚠️ 書き出すログが存在しません")
        return

    fieldnames = [
        "strategy",
        "symbol",
        "win_rate",
        "max_drawdown",
        "trade_count",
        "timestamp",
        "__log_path__"
    ]

    try:
        with open(output_path, "w", encoding="utf-8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for log in logs:
                row = {key: log.get(key, "") for key in fieldnames}
                writer.writerow(row)
        print(f"✅ 統計スコアCSVを出力しました: {output_path}")
    except Exception as e:
        print(f"⚠️ CSV出力エラー: {e}")


def aggregate_by_tag(logs: List[Dict]) -> List[Dict]:
    """
    🔥 タグ別に勝率・最大DD・取引数・昇格率を平均化・集計する
    """
    tag_groups = defaultdict(list)

    for log in logs:
        tag = log.get("tag")
        if not tag:
            continue
        tag_groups[tag].append(log)

    tag_stats = []

    for tag, items in tag_groups.items():
        win_rates = [log.get("win_rate") for log in items if isinstance(log.get("win_rate"), (int, float))]
        max_dds = [log.get("max_drawdown") for log in items if isinstance(log.get("max_drawdown"), (int, float))]
        trades = [log.get("trade_count") for log in items if isinstance(log.get("trade_count"), (int, float))]
        promoted = [log for log in items if log.get("act") == "promoted"]

        total_count = len(items)
        promotion_count = len(promoted)
        promotion_rate = round(promotion_count / total_count, 3) if total_count > 0 else 0.0

        tag_stats.append({
            "type": tag,
            "win_rate": round(sum(win_rates) / len(win_rates), 2) if win_rates else None,
            "max_drawdown": round(sum(max_dds) / len(max_dds), 2) if max_dds else None,
            "num_trades": round(sum(trades) / len(trades), 1) if trades else None,
            "promotion_rate": promotion_rate,
            "promotion_count": promotion_count,
            "count": total_count
        })

    # デフォルトは勝率降順でソート
    tag_stats.sort(key=lambda x: (x["win_rate"] is not None, x["win_rate"]), reverse=True)
    return tag_stats
