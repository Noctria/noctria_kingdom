# src/core/decision_registry.py
#!/usr/bin/env python3
# coding: utf-8
"""
🗂️ Decision Registry (Noctria)
- 王（King）や UI/Hermes が発行する「決裁（decision）」の台帳を CSV で永続化。
- 1 レコード = 1 イベント（issued / accepted / started / completed / failed / ...）。
- 既存の利用箇所（create_decision / append_event）との後方互換を維持。

主関数
- create_decision(kind, issued_by="king", intent=dict, policy_snapshot=dict) -> Decision
- append_event(decision_id, phase, payload)

補助
- get_ledger_path() / ensure_dirs()
- tail_ledger(n) / list_events(decision_id)
- rotate_ledger(max_bytes=...) でサイズ上限を超えたら自動ローテート（.1, .2 ...）

実装要点
- CSV スキーマは固定ヘッダで順序安定化（FIELDNAMES）。
- 書き込みはプロセス内ロックで競合緩和（同一プロセス内）。マルチプロセスは運用側で 1 プロセス記録を推奨。
"""

from __future__ import annotations

import csv
import json
import os
import socket
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List

# =============================================================================
# パス / 初期化
# =============================================================================

# <repo_root> を推定（src/core/decision_registry.py から 2 つ上を想定）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEDGER_DIR = PROJECT_ROOT / "data" / "decisions"
LEDGER_CSV = LEDGER_DIR / "ledger.csv"

# 固定ヘッダ（順序固定）
FIELDNAMES = [
    "ts_utc",                 # ISO8601 UTC
    "phase",                  # issued / accepted / started / completed / failed / ...
    "decision_id",            # dc_{kind}_{ts}_{host}
    "kind",                   # recheck / act / ...
    "issued_by",              # king / ui / hermes / user-id ...
    "intent_json",            # JSON string
    "policy_snapshot_json",   # JSON string
    "extra_json",             # JSON string
]

# プロセス内ロック（簡易）
_write_lock = threading.Lock()


def ensure_dirs() -> None:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)


def get_ledger_path() -> Path:
    ensure_dirs()
    return LEDGER_CSV


# =============================================================================
# データモデル
# =============================================================================

@dataclass
class Decision:
    decision_id: str
    kind: str                 # "recheck" | "act" | ...
    issued_at_utc: str
    issued_by: str            # "king" | "ui" | "hermes" | user-id 等
    intent: Dict[str, Any]    # e.g. {"strategy": "USDJPY", ...}
    policy_snapshot: Dict[str, Any]


# =============================================================================
# ユーティリティ
# =============================================================================

def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gen_id(kind: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    host = socket.gethostname().split(".")[0]
    return f"dc_{kind}_{ts}_{host}"


def _json_dumps(obj: Any) -> str:
    # ensure_ascii=False で日本語を可読に。separatorsで無駄なスペースを削減。
    return json.dumps(obj or {}, ensure_ascii=False, separators=(",", ":"))


def _write_header_if_needed(csv_path: Path) -> None:
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


# =============================================================================
# 公開 API
# =============================================================================

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


def append_event(decision_id: str, phase: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """
    既存決裁に対してイベントを追記する。
    phase 例: "accepted" | "started" | "completed" | "failed" | "cancelled" ...
    """
    # phase は簡易バリデーション（空文字禁止）
    if not phase or not isinstance(phase, str):
        phase = "unknown"
    _append_row(phase, decision_or_id=decision_id, extra=payload or {})


# =============================================================================
# 内部: CSV 追記 / ローテーション
# =============================================================================

def _append_row(phase: str, decision_or_id: Decision | str, extra: Dict[str, Any]) -> None:
    ensure_dirs()
    csv_path = get_ledger_path()

    row = {
        "ts_utc": _now_ts(),
        "phase": phase,
        "decision_id": decision_or_id.decision_id if isinstance(decision_or_id, Decision) else str(decision_or_id),
        "kind": getattr(decision_or_id, "kind", ""),
        "issued_by": getattr(decision_or_id, "issued_by", ""),
        "intent_json": _json_dumps(getattr(decision_or_id, "intent", {})),
        "policy_snapshot_json": _json_dumps(getattr(decision_or_id, "policy_snapshot", {})),
        "extra_json": _json_dumps(extra),
    }

    with _write_lock:
        _write_header_if_needed(csv_path)
        with csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row)


def rotate_ledger(max_bytes: int = 50 * 1024 * 1024, keep: int = 3) -> Optional[str]:
    """
    台帳ファイルが max_bytes を超えていたらローテートする。
    - 現在の ledger.csv を ledger.csv.1 にリネーム（既存 .1 は .2 に、… keep 世代保持）
    - 戻り値: 実行した場合は新しいファイル名、未実行なら None
    """
    ensure_dirs()
    csv_path = get_ledger_path()

    if not csv_path.exists():
        return None
    try:
        size = csv_path.stat().st_size
    except OSError:
        return None

    if size <= max_bytes:
        return None

    # 末尾から順に繰り上げ
    for i in range(keep, 0, -1):
        src = LEDGER_CSV.with_suffix(LEDGER_CSV.suffix + f".{i}")
        dst = LEDGER_CSV.with_suffix(LEDGER_CSV.suffix + f".{i+1}")
        if src.exists():
            try:
                if dst.exists():
                    dst.unlink()
                src.rename(dst)
            except OSError:
                # ベストエフォート
                pass

    # 現行を .1 へ
    rotated = LEDGER_CSV.with_suffix(LEDGER_CSV.suffix + ".1")
    try:
        if rotated.exists():
            rotated.unlink()
        csv_path.rename(rotated)
    except OSError:
        return None

    # 新規ヘッダを書いておく
    _write_header_if_needed(csv_path)
    return str(rotated)


# =============================================================================
# 便利ユーティリティ（UI/デバッグ用）
# =============================================================================

def tail_ledger(n: int = 100) -> List[Dict[str, Any]]:
    """
    台帳 CSV の末尾 n レコードを辞書で返す（メモリ効率を考慮して deque 使用）。
    JSON はデコードせず文字列のまま返す（UI 側で必要に応じて parse）。
    """
    csv_path = get_ledger_path()
    if not csv_path.exists() or n <= 0:
        return []

    buff: deque = deque(maxlen=n)
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            buff.append(row)
    return list(buff)


def list_events(decision_id: str) -> List[Dict[str, Any]]:
    """
    指定 decision_id のイベントを時系列順に返す。
    JSON はデコードせず文字列のまま返す（UI 側で必要に応じて parse）。
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


# =============================================================================
# エクスポート
# =============================================================================

__all__ = [
    "Decision",
    "create_decision",
    "append_event",
    "get_ledger_path",
    "ensure_dirs",
    "tail_ledger",
    "list_events",
    "rotate_ledger",
]
