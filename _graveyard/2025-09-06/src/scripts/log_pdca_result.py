#!/usr/bin/env python3
# coding: utf-8

"""
📜 PDCA履歴記録スクリプト
- PDCAサイクルの各段階で発生したイベントをログ(JSON)に追記する
- 各フェーズ: "generate"（戦略生成）, "evaluate"（評価）, "adopt"（採用）, "replay"（再送）, "recheck"（再評価）, "push"（GitHub保存）など
- Airflow DAGや戦略コア、GUIからも呼び出せるユーティリティ
"""

import json
from datetime import datetime
from pathlib import Path
from src.core.path_config import PDCA_LOG_DIR

PDCA_HISTORY_PATH = PDCA_LOG_DIR / "pdca_history.json"


def log_pdca_event(
    phase: str, status: str, detail: str = "", strategy_id: str = "", meta: dict = None
):
    """
    PDCAサイクルのイベントをログに追記

    Args:
        phase (str): フェーズ名（"generate", "evaluate", "adopt", "replay", "recheck", "push" など）
        status (str): 状態（"success", "fail" など）
        detail (str): 詳細説明やエラー内容
        strategy_id (str): 関連する戦略ID（省略可）
        meta (dict): 任意の追加情報
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "phase": phase,
        "status": status,
        "detail": detail,
        "strategy_id": strategy_id,
        "meta": meta or {},
    }

    # 既存ログの読み込み
    if PDCA_HISTORY_PATH.exists():
        try:
            with open(PDCA_HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    else:
        history = []

    history.append(event)

    # 保存（ディレクトリがなければ作成）
    PDCA_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PDCA_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print(f"PDCA履歴ログを追記: {event}")


# --- CLIテスト例 ---
if __name__ == "__main__":
    log_pdca_event(
        "replay", "success", detail="Airflowによる再送テスト", strategy_id="sample_strategy"
    )
