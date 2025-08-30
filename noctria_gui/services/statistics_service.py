#!/usr/bin/env python3
# coding: utf-8
"""
📊 統計データ処理サービス
- ログファイルの読み込み、フィルタリング、集計を行う
- ダッシュボードやAPIが必要とするデータ形式に整形する
"""
import json
import csv
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any, Optional

from src.core.path_config import ACT_LOG_DIR, TOOLS_DIR

def load_all_logs() -> List[Dict[str, Any]]:
    if not ACT_LOG_DIR.exists():
        return []
    all_logs = []
    for log_file in sorted(ACT_LOG_DIR.glob("*.json")):
        try:
            with log_file.open("r", encoding="utf-8") as f:
                all_logs.append(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass # エラーのあるファイルはスキップ
    return all_logs

def get_available_strategies(logs: List[Dict[str, Any]]) -> List[str]:
    return sorted(list(set(log.get("strategy", "N/A") for log in logs)))

def get_available_symbols(logs: List[Dict[str, Any]]) -> List[str]:
    return sorted(list(set(log.get("symbol", "N/A") for log in logs)))

def filter_logs(
    logs: List[Dict[str, Any]],
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    filtered = logs
    if strategy:
        filtered = [log for log in filtered if log.get("strategy") == strategy]
    if symbol:
        filtered = [log for log in filtered if log.get("symbol") == symbol]
    return filtered

def sort_logs(
    logs: List[Dict[str, Any]],
    sort_key: str,
    descending: bool = True
) -> List[Dict[str, Any]]:
    return sorted(logs, key=lambda log: log.get(sort_key, 0), reverse=descending)

def get_strategy_statistics() -> Dict[str, Any]:
    """
    ダッシュボード用の全体的な集計データを生成する。
    ★エラーの原因となっていた 'tag_distribution' を含めて返すように修正済み。
    """
    logs = load_all_logs()
    
    # タグの分布を計算
    all_tags = []
    for log in logs:
        tags = log.get("tags")
        if tags and isinstance(tags, list):
            all_tags.extend(tags)
    tag_distribution = dict(Counter(all_tags))
    
    # テンプレートが必要とする全てのキーを含んだ辞書を返す
    return {
        'strategy_count': len(get_available_strategies(logs)),
        'total_logs': len(logs),
        'tag_distribution': tag_distribution,  # <--- エラーを修正
    }

def export_statistics_to_csv(logs: List[Dict[str, Any]], output_path: Path):
    if not logs:
        return
    header = sorted(list(set(key for log in logs for key in log.keys())))
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(logs)

def compare_strategies(logs: List[Dict[str, Any]], strategy_1: str, strategy_2: str) -> Dict[str, Any]:
    filtered_1 = filter_logs(logs=logs, strategy=strategy_1)
    filtered_2 = filter_logs(logs=logs, strategy=strategy_2)
    
    def _summarize(filtered_logs):
        if not filtered_logs: return {"count": 0, "avg_win_rate": 0}
        win_rates = [log.get("win_rate", 0) for log in filtered_logs]
        return {
            "count": len(filtered_logs),
            "avg_win_rate": sum(win_rates) / len(win_rates) if win_rates else 0
        }
    return {
        "strategy_1": _summarize(filtered_1),
        "strategy_2": _summarize(filtered_2)
    }
