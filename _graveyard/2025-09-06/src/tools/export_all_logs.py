#!/usr/bin/env python3
# coding: utf-8

"""
🗂 作戦Ⅵ：Noctria Kingdom 統治ログの一括CSV出力スクリプト
- PDCAログ（発注命令）
- ACTログ（戦略昇格）
- PUSHログ（Git反映）
"""

import csv
import json
from pathlib import Path
from datetime import datetime

from core.path_config import (
    PDCA_LOG_DIR,
    ACT_LOG_DIR,
    TOOLS_DIR,
    LOGS_DIR,
)

# PUSHログが存在する場合に限り処理
PUSH_LOG_PATH = LOGS_DIR / "veritas_push_log.json"


def load_json_logs(log_dir: Path) -> list[dict]:
    logs = []
    for file in sorted(log_dir.glob("*.json")):
        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
                data["__source__"] = log_dir.name
                logs.append(data)
        except Exception as e:
            print(f"⚠️ ログ読み込み失敗: {file.name} - {e}")
    return logs


def load_push_logs() -> list[dict]:
    if not PUSH_LOG_PATH.exists():
        return []
    try:
        with open(PUSH_LOG_PATH, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    item["__source__"] = "push"
                return data
    except Exception as e:
        print(f"⚠️ PUSHログ読み込み失敗 - {e}")
    return []


def normalize_log(entry: dict) -> dict:
    return {
        "strategy": entry.get("strategy", ""),
        "symbol": entry.get("symbol", ""),
        "timestamp": entry.get("timestamp", ""),
        "status": entry.get("status", ""),
        "pushed": entry.get("pushed", ""),
        "note": entry.get("message", entry.get("note", "")),
        "source": entry.get("__source__", "")
    }


def export_all_logs():
    all_logs = []

    pdca_logs = load_json_logs(PDCA_LOG_DIR)
    act_logs = load_json_logs(ACT_LOG_DIR)
    push_logs = load_push_logs()

    for entry in pdca_logs + act_logs + push_logs:
        all_logs.append(normalize_log(entry))

    if not all_logs:
        print("⚠️ 出力対象のログが存在しません")
        return

    output_dir = TOOLS_DIR / "統治記録"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"noctria_governance_logs_{timestamp}.csv"

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["strategy", "symbol", "timestamp", "status", "pushed", "note", "source"]
        )
        writer.writeheader()
        writer.writerows(all_logs)

    print(f"✅ 統治ログCSVを出力しました: {output_path}")


if __name__ == "__main__":
    export_all_logs()
