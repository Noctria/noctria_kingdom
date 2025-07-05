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
    - strategy: 戦略名で絞り込み
    - symbol: 通貨ペアで絞り込み
    - start_date/end_date: ISO形式文字列（例: '2025-07-01'）
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
    - 必須項目: strategy, symbol, win_rate, max_drawdown, trade_count, timestamp
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
    - 勝率 / 最大ドローダウン / 取引回数 など主要項目を抽出
    """
    if not logs:
        print("⚠️ 書き出すログが存在しません")
        return

    fieldnames = [
        "strategy",        # 戦略名
        "symbol",          # 通貨ペア
        "win_rate",        # 勝率（float）
        "max_drawdown",    # 最大DD（float）
        "trade_count",     # 取引回数
        "timestamp",       # 評価タイムスタンプ
        "__log_path__",    # 元ログファイルのパス
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for log in logs:
            row = {key: log.get(key, "") for key in fieldnames}
            writer.writerow(row)

    print(f"✅ 統計スコアCSVを出力しました: {output_path}")
