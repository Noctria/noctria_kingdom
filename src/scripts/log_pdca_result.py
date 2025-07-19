#!/usr/bin/env python3
# coding: utf-8

"""
📜 PDCA履歴記録スクリプト
- PDCAサイクルの各段階で発生したイベントをログ(JSON)に追記する
- 各フェーズ: "generate"（戦略生成）, "evaluate"（評価）, "adopt"（採用）, "replay"（再送）, "recheck"（再評価）, "push"（GitHub保存）
- Airflow DAGや戦略コア、GUIからも呼び出せる
"""

import json
from datetime import datetime
from pathlib import Path
from src.core.path_config import PDCA_LOG_DIR

PDCA_HISTORY_PATH = PDCA_LOG_DIR / "pdca_history.json"

def log_pdca_event(phase: str, status: str, detail: str = "", strategy_id: str = "", meta: dict = None):
    """
    PDCAサイクルのイベントをログに追記
    - phase: フェーズ名（"generate", "evaluate", "adopt", "replay", "recheck", "push" など）
    - status: 状態（"success", "fail" など）
    - detail: 詳細説明やエラー内容
    - strategy_id: 関連する戦略ID（省略可）
    - meta: 任意の追加情報(dict)
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "phase": phase,
        "status": status,
        "detail": detail,
        "strategy_id": strategy_id,
        "meta": meta or {}
    }

    # 既存ログの読み込み
    if PDCA_HISTORY_PATH.exists():
        with open(PDCA_HISTORY_PATH, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except Exception:
                history = []
    else:
        history = []

    history.append(event)

    # 保存
    PDCA_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PDCA_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print(f"PDCA履歴ログを追記: {event}")

# --- CLIテスト例 ---
if __name__ == "__main__":
    log_pdca_event("replay", "success", detail="Airflowによる再送テスト", strategy_id="sample_strategy")
