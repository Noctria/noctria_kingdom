# src/core/policy_engine.py
# -*- coding: utf-8 -*-
"""
👑 Noctria King Policy Engine (v1.0)

目的:
- 王の意思決定ポリシーを一元管理（採用/再評価の可否、しきい値、メンテナンスフラグ等）
- スナップショット(get_snapshot)をGUI/台帳/トリガAPIから参照できるように提供
- 環境変数とファイルの両方で上書き可能、フェイルセーフで空/既定にフォールバック

主なAPI:
- get_policy() -> dict             : 現在有効なポリシー（ファイル+ENV反映）
- get_snapshot() -> dict           : 時刻や由来込みのスナップショット
- can_adopt(metrics: dict) -> (bool, reason)
- can_recheck(context: dict) -> (bool, reason)
- save_policy(p: dict) -> None     : 任意でポリシーを保存（ローカル運用用）
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ルート推定
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
POLICY_DIR = DATA_DIR / "policy"
POLICY_DIR.mkdir(parents=True, exist_ok=True)
POLICY_JSON = POLICY_DIR / "policy.json"

# 既定値（環境によっては env で上書き）
DEFAULT_POLICY = {
    "version": "1.0",
    "adoption": {
        # 勝率 >= (0-1), DD <= (正値で%想定)、最低トレード数
        "min_win_rate": 0.60,         # 60%
        "max_drawdown": 0.20,         # 20%
        "min_trades": 30,
        # 追加条件
        "require_recent": True,       # 直近結果必須
        "recent_days": 30,            # 直近30日内の評価あり
        "dry_run_block": False,       # Trueだとdry_runは採用不可
    },
    "recheck": {
        "cooldown_minutes": 10,       # 同一戦略の連続再評価のクールダウン
        "limit_per_hour": 60,         # 全体レート制限（簡易）
        "allow_without_reason": True, # 理由なし再評価を許容するか
    },
    "maintenance": {
        "read_only": False,           # Trueなら採用不可、再評価のみ許容
        "suspend_triggers": False,    # Trueなら全トリガを禁止（UI/自動含む）
    },
    "notes": "Edit data/policy/policy.json or env to customize.",
}

# 環境変数キー（あれば優先）
ENV_KEYS = {
    "adoption.min_win_rate": "NOCTRIA_POLICY_ADOPT_MIN_WR",
    "adoption.max_drawdown": "NOCTRIA_POLICY_ADOPT_MAX_DD",
    "adoption.min_trades": "NOCTRIA_POLICY_ADOPT_MIN_TRADES",
    "adoption.require_recent": "NOCTRIA_POLICY_ADOPT_REQUIRE_RECENT",
    "adoption.recent_days": "NOCTRIA_POLICY_ADOPT_RECENT_DAYS",
    "adoption.dry_run_block": "NOCTRIA_POLICY_ADOPT_DRYRUN_BLOCK",
    "recheck.cooldown_minutes": "NOCTRIA_POLICY_RECHECK_COOLDOWN_MIN",
    "recheck.limit_per_hour": "NOCTRIA_POLICY_RECHECK_LIMIT_PER_HOUR",
    "recheck.allow_without_reason": "NOCTRIA_POLICY_RECHECK_ALLOW_NO_REASON",
    "maintenance.read_only": "NOCTRIA_POLICY_MAINT_READ_ONLY",
    "maintenance.suspend_triggers": "NOCTRIA_POLICY_MAINT_SUSPEND",
}

def _as_bool(s: Optional[str], default: bool) -> bool:
    if s is None:
        return default
    return str(s).strip().lower() in ("1", "true", "yes", "on")

def _as_float(s: Optional[str], default: float) -> float:
    try:
        return float(s) if s is not None else default
    except Exception:
        return default

def _as_int(s: Optional[str], default: int) -> int:
    try:
        return int(s) if s is not None else default
    except Exception:
        return default

def _load_file_policy() -> Dict[str, Any]:
    if POLICY_JSON.exists():
        try:
            return json.loads(POLICY_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_POLICY.copy()

def _merge_env(policy: Dict[str, Any]) -> Dict[str, Any]:
    # adoption
    a = policy.setdefault("adoption", {}).copy()
    a["min_win_rate"] = _as_float(os.getenv(ENV_KEYS["adoption.min_win_rate"]), a.get("min_win_rate", 0.60))
    a["max_drawdown"] = _as_float(os.getenv(ENV_KEYS["adoption.max_drawdown"]), a.get("max_drawdown", 0.20))
    a["min_trades"] = _as_int(os.getenv(ENV_KEYS["adoption.min_trades"]), a.get("min_trades", 30))
    a["require_recent"] = _as_bool(os.getenv(ENV_KEYS["adoption.require_recent"]), a.get("require_recent", True))
    a["recent_days"] = _as_int(os.getenv(ENV_KEYS["adoption.recent_days"]), a.get("recent_days", 30))
    a["dry_run_block"] = _as_bool(os.getenv(ENV_KEYS["adoption.dry_run_block"]), a.get("dry_run_block", False))
    policy["adoption"] = a

    # recheck
    r = policy.setdefault("recheck", {}).copy()
    r["cooldown_minutes"] = _as_int(os.getenv(ENV_KEYS["recheck.cooldown_minutes"]), r.get("cooldown_minutes", 10))
    r["limit_per_hour"] = _as_int(os.getenv(ENV_KEYS["recheck.limit_per_hour"]), r.get("limit_per_hour", 60))
    r["allow_without_reason"] = _as_bool(
        os.getenv(ENV_KEYS["recheck.allow_without_reason"]), r.get("allow_without_reason", True)
    )
    policy["recheck"] = r

    # maintenance
    m = policy.setdefault("maintenance", {}).copy()
    m["read_only"] = _as_bool(os.getenv(ENV_KEYS["maintenance.read_only"]), m.get("read_only", False))
    m["suspend_triggers"] = _as_bool(os.getenv(ENV_KEYS["maintenance.suspend_triggers"]), m.get("suspend_triggers", False))
    policy["maintenance"] = m

    return policy

def get_policy() -> Dict[str, Any]:
    """ファイル＋ENVを反映した現在有効なポリシーを返す。"""
    p = _load_file_policy()
    p = _merge_env(p)
    if "version" not in p:
        p["version"] = "1.0"
    return p

def save_policy(p: Dict[str, Any]) -> None:
    """ローカル編集用: ポリシーを保存（環境変数は上書きしない）。"""
    POLICY_JSON.parent.mkdir(parents=True, exist_ok=True)
    POLICY_JSON.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def get_snapshot() -> Dict[str, Any]:
    """GUI/台帳に渡すためのスナップショット。"""
    p = get_policy()
    return {
        "captured_at_utc": _now_utc_iso(),
        "source": {
            "file": str(POLICY_JSON),
            "env_overrides": {k: v for k, v in ENV_KEYS.items() if os.getenv(v) is not None},
        },
        "policy": p,
    }

# ------------------------------------------------------------
# 判定系（最小実装）
# ------------------------------------------------------------
def can_adopt(metrics: Dict[str, Any], *, dry_run: bool = False, recent_days: Optional[int] = None) -> Tuple[bool, str]:
    """
    metricsの想定:
      - win_rate: 0-1 の小数
      - max_drawdown: 0-1 の小数（正値で%想定。0.18=18%）
      - trades: int
      - last_evaluated_at: ISO8601 or None
    """
    p = get_policy()
    if p["maintenance"].get("suspend_triggers"):
        return False, "suspend_triggers=true"
    if p["maintenance"].get("read_only"):
        return False, "read_only=true"

    a = p["adoption"]
    wr = _coerce_float(metrics.get("win_rate"))
    dd = _coerce_float(metrics.get("max_drawdown"))
    tr = _coerce_int(metrics.get("trades"), default=0)

    if wr is None or dd is None:
        return False, "missing win_rate or max_drawdown"
    if wr < float(a["min_win_rate"]):
        return False, f"win_rate<{a['min_win_rate']}"
    if dd > float(a["max_drawdown"]):
        return False, f"max_drawdown>{a['max_drawdown']}"
    if tr < int(a["min_trades"]):
        return False, f"trades<{a['min_trades']}"

    if dry_run and a.get("dry_run_block", False):
        return False, "dry_run_blocked"

    if a.get("require_recent", True):
        days = int(recent_days or a.get("recent_days", 30))
        if not _within_days(metrics.get("last_evaluated_at"), days):
            return False, f"no recent eval within {days}d"

    return True, "ok"

def can_recheck(context: Dict[str, Any]) -> Tuple[bool, str]:
    """
    contextの例:
      - reason: str|None
      - last_recheck_at: ISO8601|None
      - count_last_hour: int|None
    ※ 実際のクールダウン/レート制限の厳密判定は観測ログや別レイヤで。
      ここでは軽いガードのみ。
    """
    p = get_policy()
    if p["maintenance"].get("suspend_triggers"):
        return False, "suspend_triggers=true"

    r = p["recheck"]
    reason = (context.get("reason") or "").strip()
    allow_no_reason = bool(r.get("allow_without_reason", True))
    if not reason and not allow_no_reason:
        return False, "reason required"

    # 軽いレート制限（呼び出し側が埋めれば見る、無ければ通す）
    cnt = _coerce_int(context.get("count_last_hour"))
    if cnt is not None and cnt >= int(r.get("limit_per_hour", 60)):
        return False, "rate limited"

    # クールダウン（呼び出し側が直近時刻を渡した時のみ判定）
    last = context.get("last_recheck_at")
    if last and _within_minutes(last, int(r.get("cooldown_minutes", 10))) is False:
        return False, "cooldown"

    return True, "ok"

# ------------------------------------------------------------
# 小物ユーティリティ
# ------------------------------------------------------------
def _coerce_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _coerce_int(v: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default

def _parse_iso8601(s: Any) -> Optional[datetime]:
    if not s or not isinstance(s, str):
        return None
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _within_days(iso: Any, days: int) -> bool:
    dt = _parse_iso8601(iso)
    if not dt:
        return False
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() <= days * 86400

def _within_minutes(iso: Any, minutes: int) -> Optional[bool]:
    dt = _parse_iso8601(iso)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() <= minutes * 60
