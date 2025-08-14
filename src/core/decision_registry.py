# src/core/decision_registry.py
#!/usr/bin/env python3
# coding: utf-8
"""
🗂️ Decision Registry (Noctria)
- 王（King）やUI/Hermesが発行する「決裁（decision）」の台帳。
- 1レコード=1イベント（issued/accepted/started/completed/failed/...）をCSV追記で永続化。
- 既存の利用箇所（create_decision / append_event）との後方互換を維持。

主関数
- create_decision(kind, issued_by="king", intent=dict, policy_snapshot=dict) -> Decision
- append_event(decision_id, phase, payload)

補助
- get_ledger_path() / ensure_dirs()
- tail_ledger(n) / list_events(decision_id) などの軽ユーティリティ（任意でUIから参照可）

実装方針
- CSVは簡素なスキーマ: ts_utc, phase, decision_id, kind, issued_by, intent_json, policy_snapshot_json, extra_json
- 書き込みはプロセス内のロックで競合緩和（同一プロセス内）。マルチプロセスは運用側で1プロセス記録を推奨。
"""

from __future__ import annotations

import csv
import json
import socket
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List

# -----------------------------------------------------------------------------
# パス/初期化
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # <repo_root>
LEDGER_DIR = PROJECT_ROOT / "data" / "decisions"
LEDGER_CSV = LEDGER_DIR / "ledger.csv"

# プロセス内ロック（簡易）
_write_lock = threading.Lock()

def ensure_dirs() -> None:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)

def get_ledger_path() -> Path:
    ensure_dirs()
    return LEDGER_CSV

# -----------------------------------------------------------------------------
# データモデル
# -----------------------------------------------------------------------------
@dataclass
class Decision:
    decision_id: str
    kind: str                 # "recheck" | "act" | ...
    issued_at_utc: str
    issued_by: str            # "king" | "ui" | "hermes" | user-id 等
    intent: Dict[str, Any]    # e.g. {"strategy": "..."}
    policy_snapshot: Dict[str, Any]

# -----------------------------------------------------------------------------
# ユーティリティ
# -----------------------------------------------------------------------------
def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _gen_id(kind: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    host = socket.gethostname().split(".")[0]
    return f"dc_{kind}_{ts}_{host}"

# -----------------------------------------------------------------------------
# 公開API
# -----------------------------------------------------------------------------
def create_decision(
    kind: str,
    *,
    issued_by: str = "king",
    intent: Optional[Dict[str, Any]] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> Decision:
    """
    新しい決裁を発行し、台帳に `issued` イベントを追記して返す。
    """
    d = Decision(
        decision_id=_gen_id(kind),
        kind=kind,
        issued_at_utc=_now_ts(),
        issued_by=issued_by,
        intent=intent or {},
        policy_snapshot=policy_snapshot or {},
    )
    _append_row("issued", d, extra={})
    return d

def append_event(decision_id: str, phase: str, payload: Dict[str, Any]) -> None:
    """
    既存決裁に対してイベントを追記する。
    phase 例: "accepted" | "started" | "completed" | "failed" | "cancelled" ...
    """
    # phase は簡易バリデーション（空文字禁止）
    if not phase or not isinstance(phase, str):
        phase = "unknown"
    _append_row(phase, decision_id, extra=payload or {})

# -----------------------------------------------------------------------------
# 内部: CSV 追記
# -----------------------------------------------------------------------------
def _append_row(phase: str, decision_or_id: Decision | str, extra: Dict[str, Any]) -> None:
    ensure_dirs()

    row = {
        "ts_utc": _now_ts(),
        "phase": phase,
        "decision_id": decision_or_id.decision_id if isinstance(decision_or_id, Decision) else str(decision_or_id),
        "kind": getattr(decision_or_id, "kind", ""),
        "issued_by": getattr(decision_or_id, "issued_by", ""),
        "intent_json": json.dumps(getattr(decision_or_id, "intent", {}), ensure_ascii=False),
        "policy_snapshot_json": json.dumps(getattr(decision_or_id, "policy_snapshot", {}), ensure_ascii=False),
        "extra_json": json.dumps(extra or {}, ensure_ascii=False),
    }

    header = list(row.keys())
    csv_path = get_ledger_path()
    write_header = not csv_path.exists()

    with _write_lock:
        with csv_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=header)
            if write_header:
                w.writeheader()
            w.writerow(row)

# -----------------------------------------------------------------------------
# 便利ユーティリティ（UI/デバッグ用・オプション）
# -----------------------------------------------------------------------------
def tail_ledger(n: int = 100) -> List[Dict[str, Any]]:
    """
    台帳CSVの末尾 n レコードを辞書で返す（メモリ効率はほどほど）。
    pandas 依存にしない軽量版。
    """
    csv_path = get_ledger_path()
    if not csv_path.exists() or n <= 0:
        return []

    # 単純読み込み（ファイルサイズが巨大なら別途最適化検討）
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)[-n:]
    return rows

def list_events(decision_id: str) -> List[Dict[str, Any]]:
    """
    指定 decision_id のイベントを時系列順に返す。
    """
    csv_path = get_ledger_path()
    if not csv_path.exists():
        return []

    out: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("decision_id") == decision_id:
                out.append(r)
    # ts_utc 昇順で整列（パース失敗時は順序維持）
    try:
        out.sort(key=lambda r: r.get("ts_utc") or "")
    except Exception:
        pass
    return out

__all__ = [
    "Decision",
    "create_decision",
    "append_event",
    "get_ledger_path",
    "ensure_dirs",
    "tail_ledger",
    "list_events",
]
