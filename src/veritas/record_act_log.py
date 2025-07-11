#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas 評価結果を Act ログ（昇格戦略ログ）として記録
- 対象: veritas_eval_result.json
- 出力先: /data/act_logs/{戦略名}_{timestamp}.json
- pushed 状態も push_logs から照合し記録
- 重複記録の防止機構付き
"""

import json
from datetime import datetime
from pathlib import Path

# ✅ 王国の地図
from core.path_config import VERITAS_EVAL_LOG, DATA_DIR

ACT_LOG_DIR = DATA_DIR / "act_logs"
PUSH_LOG_PATH = DATA_DIR / "push_logs" / "push_history.json"

# ========================================
# 🔍 すでに記録済みかをチェック
# ========================================
def is_already_recorded(strategy_name: str) -> bool:
    if not ACT_LOG_DIR.exists():
        return False
    for file in ACT_LOG_DIR.glob(f"{strategy_name.replace('.py','')}_*.json"):
        return True
    return False

# ========================================
# 🔍 push履歴から該当戦略がPushされたか確認
# ========================================
def is_pushed(strategy_name: str, timestamp: str) -> bool:
    if not PUSH_LOG_PATH.exists():
        return False

    with open(PUSH_LOG_PATH, "r", encoding="utf-8") as f:
        push_logs = json.load(f)

    for entry in push_logs:
        if entry.get("strategy") == strategy_name:
            # 時刻が近ければOK（数秒のズレ容認）
            pushed_time = datetime.fromisoformat(entry["timestamp"])
            act_time = datetime.fromisoformat(timestamp)
            if abs((pushed_time - act_time).total_seconds()) < 60:
                return True
    return False

# ========================================
# 🧠 Actログ生成
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
        if not entry.get("adopted", False):
            continue

        strategy_name = entry.get("strategy_name", "unknown_strategy.py")

        if is_already_recorded(strategy_name):
            print(f"⚠️ すでに記録済のためスキップ: {strategy_name}")
            continue

        timestamp = datetime.utcnow().replace(microsecond=0).isoformat()

        act_log = {
            "timestamp": timestamp,
            "strategy": strategy_name,
            "score": entry.get("score", {}),
            "reason": entry.get("reason", "評価基準を満たしたため"),
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
