#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas Machina - 評価合格戦略のActログ記録スクリプト（ML専用）
- 入力: ML評価ログ（veritas_eval_result.json）
- 出力: /data/act_logs/{戦略名}_{timestamp}.json
- Push状態もpush_logsから参照
- 重複記録の防止
"""

import json
from datetime import datetime
from pathlib import Path

# 王国の地図（パス定義）
from src.core.path_config import VERITAS_EVAL_LOG, DATA_DIR

ACT_LOG_DIR = DATA_DIR / "act_logs"
PUSH_LOG_PATH = DATA_DIR / "push_logs" / "push_history.json"

# ========================================
# 🔍 すでに記録済みかチェック
# ========================================
def is_already_recorded(strategy_name: str) -> bool:
    if not ACT_LOG_DIR.exists():
        return False
    for file in ACT_LOG_DIR.glob(f"{strategy_name.replace('.py','')}_*.json"):
        return True
    return False

# ========================================
# 🔍 push履歴から該当戦略がPushされたか
# ========================================
def is_pushed(strategy_name: str, timestamp: str) -> bool:
    if not PUSH_LOG_PATH.exists():
        return False

    with open(PUSH_LOG_PATH, "r", encoding="utf-8") as f:
        push_logs = json.load(f)

    for entry in push_logs:
        if entry.get("strategy") == strategy_name:
            try:
                pushed_time = datetime.fromisoformat(entry["timestamp"])
                act_time = datetime.fromisoformat(timestamp)
                if abs((pushed_time - act_time).total_seconds()) < 60:
                    return True
            except Exception:
                continue
    return False

# ========================================
# 🧠 Actログ生成（ML評価合格のみ）
# ========================================
def record_act_log():
    if not VERITAS_EVAL_LOG.exists():
        print(f"❌ 評価ログが見つかりません: {VERITAS_EVAL_LOG}")
        return

    with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
        results = json.load(f)

    ACT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    count = 0

    for entry in results:
        # 採用判定キーを現行仕様（MLは"passed"）に揃える
        if not entry.get("passed", False):
            continue

        # 戦略名キーを統一（現行評価ログは"strategy"）
        strategy_name = entry.get("strategy", entry.get("strategy_name", "unknown_strategy.py"))

        if is_already_recorded(strategy_name):
            print(f"⚠️ すでに記録済のためスキップ: {strategy_name}")
            continue

        timestamp = datetime.utcnow().replace(microsecond=0).isoformat()

        # 必要な項目が評価ログにあれば取り込む
        act_log = {
            "timestamp": timestamp,
            "strategy": strategy_name,
            "score": {
                "final_capital": entry.get("final_capital"),
                "win_rate": entry.get("win_rate"),
                "max_drawdown": entry.get("max_drawdown"),
                "total_trades": entry.get("total_trades")
            },
            "reason": entry.get("reason", "ML評価基準を満たしたため"),
            "pushed": is_pushed(strategy_name, timestamp)
        }

        filename = f"{strategy_name.replace('.py','')}_{timestamp.replace(':','-')}.json"
        out_path = ACT_LOG_DIR / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(act_log, f, indent=2, ensure_ascii=False)

        count += 1
        print(f"✅ Actログを記録しました: {out_path}")

    if count == 0:
        print("ℹ️ 採用された新規戦略はありませんでした。")
    else:
        print(f"📜 王国の記録: {count} 件の昇格ログを記録しました。")

# ========================================
# 🏁 実行
# ========================================
if __name__ == "__main__":
    record_act_log()
