#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas Machina - 評価合格戦略のActログ記録スクリプト（ML専用） + 観測DBヘルパ

このモジュールは2つの用途を提供します：

1) ML評価の Act ログを JSON に記録（既存機能）
   - 入力: ML評価ログ（veritas_eval_result.json）
   - 出力: /data/act_logs/{戦略名}_{timestamp}.json
   - Push状態も push_logs から参照
   - 重複記録の防止

2) 観測DB（SQLite）への最小記録（新規ヘルパ）
   - テーブル: obs_plan_runs / obs_infer_calls（存在しなければ自動作成）
   - 外部ネットや Postgres 不要、オフラインCI向けの最小実装
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

# 王国の地図（パス定義）
from src.core.path_config import DATA_DIR, VERITAS_EVAL_LOG

# =========================
# 既存: Act ログの出力先
# =========================
ACT_LOG_DIR = DATA_DIR / "act_logs"
PUSH_LOG_PATH = DATA_DIR / "push_logs" / "push_history.json"

# =========================
# 新規: 観測DBの場所（SQLite）
# =========================
#   - CI で書き込み確認するための最小DB
#   - 既定: <DATA_DIR>/codex_reports/pdca_log.db
OBS_DB_PATH = DATA_DIR / "codex_reports" / "pdca_log.db"


# =============================================================================
# 既存機能: ML Act ログ記録
# =============================================================================
def is_already_recorded(strategy_name: str) -> bool:
    if not ACT_LOG_DIR.exists():
        return False
    for file in ACT_LOG_DIR.glob(f"{strategy_name.replace('.py', '')}_*.json"):
        return True
    return False


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


def record_act_log() -> None:
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
                "total_trades": entry.get("total_trades"),
            },
            "reason": entry.get("reason", "ML評価基準を満たしたため"),
            "pushed": is_pushed(strategy_name, timestamp),
        }

        filename = f"{strategy_name.replace('.py', '')}_{timestamp.replace(':', '-')}.json"
        out_path = ACT_LOG_DIR / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(act_log, f, indent=2, ensure_ascii=False)

        count += 1
        print(f"✅ Actログを記録しました: {out_path}")

    if count == 0:
        print("ℹ️ 採用された新規戦略はありませんでした。")
    else:
        print(f"📜 王国の記録: {count} 件の昇格ログを記録しました。")


# =============================================================================
# 新規機能: 観測DB（SQLite）ヘルパ
# =============================================================================
def _ensure_obs_schema(db_path: Path) -> None:
    """必要なテーブルがなければ作成する。"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn, closing(conn.cursor()) as cur:
        # obs_plan_runs
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS obs_plan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL
            )
            """
        )
        # obs_infer_calls（必要に応じてカウントを見るテスト対策）
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS obs_infer_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def record_obs_plan_run(db_path: Path | None = None) -> None:
    """
    観測：計画ランを1件だけ記録。
    - テーブルが無ければ自動作成
    - 返り値なし（副作用 = 1行INSERT）
    """
    dbp = Path(db_path) if db_path else OBS_DB_PATH
    _ensure_obs_schema(dbp)
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    with sqlite3.connect(dbp) as conn, closing(conn.cursor()) as cur:
        cur.execute("INSERT INTO obs_plan_runs(created_at) VALUES (?)", (now,))
        conn.commit()
    print(f"[obs] +1 obs_plan_runs @ {dbp}")


def record_obs_infer_call(db_path: Path | None = None) -> None:
    """
    観測：推論呼び出しを1件だけ記録。
    - テーブルが無ければ自動作成
    - 返り値なし（副作用 = 1行INSERT）
    """
    dbp = Path(db_path) if db_path else OBS_DB_PATH
    _ensure_obs_schema(dbp)
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    with sqlite3.connect(dbp) as conn, closing(conn.cursor()) as cur:
        cur.execute("INSERT INTO obs_infer_calls(created_at) VALUES (?)", (now,))
        conn.commit()
    print(f"[obs] +1 obs_infer_calls @ {dbp}")


# =============================================================================
# 🏁 実行
# =============================================================================
if __name__ == "__main__":
    # 既存の CLI 的挙動は維持：評価ログがあれば Act ログを記録
    record_act_log()
