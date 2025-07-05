#!/usr/bin/env python3
# coding: utf-8

import json
from datetime import datetime
from pathlib import Path

# ========================================
# 🧠 Veritas 戦略評価ログ → 採用記録へ
# ========================================

from core.path_config import VERITAS_EVAL_LOG, DATA_DIR

# 📁 採用履歴ログディレクトリ
ACT_LOG_DIR = DATA_DIR / "act_logs"
ACT_LOG_DIR.mkdir(parents=True, exist_ok=True)

def load_latest_eval_result() -> dict:
    """評価ログファイルから最新戦略の評価結果を取得"""
    if not VERITAS_EVAL_LOG.exists():
        print("❌ 評価ログが存在しません:", VERITAS_EVAL_LOG)
        return {}

    with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        print("❌ 評価ログに戦略情報が見つかりません")
        return {}

    latest = data[-1]
    print(f"✅ 最新の戦略評価を取得: {latest.get('strategy')}")
    return latest

def save_act_log(strategy_info: dict, reason: str = "評価基準を満たしたため"):
    """採用戦略の記録を保存"""
    log_entry = {
        "strategy": strategy_info.get("strategy"),
        "score": strategy_info.get("score"),
        "reason": reason,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }

    timestamp = log_entry["timestamp"].replace(":", "-")
    log_path = ACT_LOG_DIR / f"{timestamp}.json"

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, indent=2, ensure_ascii=False)

    print("📜 採用戦略を記録しました:", log_path)
    print("📦 内容:", log_entry)

def record_latest_act():
    """最新の戦略評価を Act フェーズとして記録"""
    latest = load_latest_eval_result()
    if latest:
        save_act_log(latest)

if __name__ == "__main__":
    record_latest_act()
