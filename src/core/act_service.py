# src/core/act_service.py
#!/usr/bin/env python3
# coding: utf-8
"""
Act (Adopt) Service

- 評価済み戦略を正式採用としてプロジェクトに取り込むユーティリティ
- 可能なら Git へコミット/タグ付け（無ければフォールバックでファイルコピーのみ）
- 採用ログを CSV に記録
- ★ ポリシー審査（policy_engine.can_adopt）を通過した場合のみ採用（force で上書き可）
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# パス解決（path_config が無くても動く）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

try:
    from src.core.path_config import (  # type: ignore
        STRATEGIES_VERITAS_GENERATED_DIR as _GEN_DIR,
        STRATEGIES_DIR as _STR_DIR,
        PDCA_LOG_DIR as _PDCA_DIR,
    )
except Exception:
    _GEN_DIR = SRC_DIR / "strategies" / "veritas_generated"
    _STR_DIR = SRC_DIR / "strategies"
    _PDCA_DIR = PROJECT_ROOT / "data" / "pdca_logs" / "veritas_orders"

ADOPTED_DIR = _STR_DIR / "adopted"
ADOPTED_DIR.mkdir(parents=True, exist_ok=True)
_PLOG_DIR = _PDCA_DIR
_PLOG_DIR.mkdir(parents=True, exist_ok=True)

# policy_engine は存在しない環境でも動くように
try:
    from src.core.policy_engine import can_adopt, get_snapshot  # type: ignore
except Exception:
    can_adopt = None  # type: ignore
    get_snapshot = None  # type: ignore


@dataclass
class ActResult:
    ok: bool
    message: str
    strategy: str
    committed: bool
    tag: Optional[str]
    output_path: Optional[Path]
    details: Dict[str, Any]


def _git_available(repo_dir: Path) -> bool:
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return r.returncode == 0 and r.stdout.decode().strip() == "true"
    except Exception:
        return False


def _git_commit_and_tag(repo_dir: Path, rel_path: str, message: str, tag: Optional[str]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    committed = False
    try:
        subprocess.run(["git", "add", rel_path], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=repo_dir, check=True)
        committed = True
        if tag:
            subprocess.run(["git", "tag", tag], cwd=repo_dir, check=True)
        return True, tag, {}
    except subprocess.CalledProcessError as e:
        return committed, None, {"git_error": str(e), "returncode": e.returncode}
    except Exception as e:
        return committed, None, {"git_error": str(e)}


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _read_latest_eval_metrics(strategy: str) -> Dict[str, Any]:
    """
    PDCA 日別CSV（rechecks_*.csv）から対象戦略の最新行を探し、採用基準で使うメトリクスを返す。
    返却: {win_rate, max_drawdown, trades, last_evaluated_at}（無ければ None）
    ※ pandas 非依存、純標準の csv で実装
    """
    metrics = {
        "win_rate": None,
        "max_drawdown": None,
        "trades": None,
        "last_evaluated_at": None,
        "_source_file": None,
    }

    try:
        files = sorted(_PLOG_DIR.glob("rechecks_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        files = []

    if not files:
        return metrics

    for fp in files:
        try:
            with fp.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                # 新しいファイルから順に、ファイル内は末尾行が新しいとは限らないため全走査
                latest_row = None
                latest_ts = None
                for row in reader:
                    if (row.get("strategy") or "").strip() != strategy:
                        continue
                    ts = row.get("evaluated_at") or row.get("timestamp") or ""
                    # 文字列比較に頼らず、可能なら ISO 解析
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        dt = None
                    if latest_ts is None or (dt and latest_ts and dt > latest_ts) or (dt and latest_ts is None):
                        latest_ts = dt
                        latest_row = row
                if latest_row:
                    metrics["win_rate"] = _safe_float(latest_row.get("winrate_new") or latest_row.get("win_rate"))
                    metrics["max_drawdown"] = _safe_float(latest_row.get("maxdd_new") or latest_row.get("max_drawdown"))
                    metrics["trades"] = _safe_float(latest_row.get("trades_new") or latest_row.get("trades"))
                    metrics["last_evaluated_at"] = (latest_row.get("evaluated_at") or latest_row.get("timestamp") or None)
                    metrics["_source_file"] = fp.name
                    return metrics
        except Exception:
            # 壊れたCSVはスキップ
            continue

    return metrics


def adopt_strategy(
    strategy: str,
    *,
    reason: str = "",
    decision_id: Optional[str] = None,
    dry_run: bool = False,
    force: bool = False,
) -> ActResult:
    """
    veritas_generated/{strategy}.py -> strategies/adopted/{strategy}.py へ採用。
    Git が使える場合は add/commit + tag まで。
    - policy_engine.can_adopt による審査を実施（force で上書き可能）
    - 環境変数 NOCTRIA_ACT_FORCE=1 でも強制採用
    """
    src = _GEN_DIR / f"{strategy}.py"
    if not src.exists():
        return ActResult(False, f"source not found: {src}", strategy, False, None, None, {})

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dst = ADOPTED_DIR / f"{strategy}.py"

    # ---- ポリシー審査 -------------------------------------------------------
    force_env = str(os.getenv("NOCTRIA_ACT_FORCE", "")).strip().lower() in ("1", "true", "yes", "on")
    force_final = bool(force or force_env)

    policy_ok: Optional[bool] = None
    policy_reason: str = ""
    policy_snapshot: Dict[str, Any] = {}

    # メトリクス取得（ログが無い/不足でもできる限り渡す）
    met = _read_latest_eval_metrics(strategy)

    if get_snapshot:
        try:
            policy_snapshot = dict(get_snapshot())
        except Exception:
            policy_snapshot = {}

    if can_adopt:
        try:
            ok, reason_msg = can_adopt(
                {
                    "win_rate": met["win_rate"],
                    "max_drawdown": met["max_drawdown"],
                    "trades": met["trades"],
                    "last_evaluated_at": met["last_evaluated_at"],
                }
            )
            policy_ok = bool(ok)
            policy_reason = reason_msg or ""
        except Exception as e:
            policy_ok = None
            policy_reason = f"policy_engine error: {e}"
    else:
        policy_ok = None
        policy_reason = "policy_engine unavailable"

    if policy_ok is False and not force_final and not dry_run:
        # ブロック
        return ActResult(
            False,
            f"Adoption blocked by policy: {policy_reason}",
            strategy,
            False,
            None,
            None,
            {
                "policy_ok": policy_ok,
                "policy_reason": policy_reason,
                "metrics": met,
                "policy_snapshot": policy_snapshot,
            },
        )

    # ---- 実行（DRY-RUN） ---------------------------------------------------
    commit_msg = f"adopt(strategy={strategy}) reason='{reason}' decision_id={decision_id or '-'} at {ts}"
    tag_name = f"adopted/{strategy}/{ts}"

    if dry_run:
        return ActResult(
            True,
            "[DRY-RUN] adoption simulated",
            strategy,
            False,
            tag_name,
            dst,
            {
                "src": str(src),
                "dst": str(dst),
                "commit_message": commit_msg,
                "policy_ok": policy_ok,
                "policy_reason": policy_reason,
                "forced": force_final,
                "metrics": met,
            },
        )

    # ---- 1) ファイルコピー（上書きOK） --------------------------------------
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

    # ---- 2) Git コミット＆タグ ---------------------------------------------
    committed = False
    tag_applied: Optional[str] = None
    git_info: Dict[str, Any] = {}
    if _git_available(PROJECT_ROOT):
        committed, tag_applied, git_info = _git_commit_and_tag(
            PROJECT_ROOT, str(dst.relative_to(PROJECT_ROOT)), commit_msg, tag_name
        )

    # ---- 3) 採用ログ CSV 追記 ----------------------------------------------
    log_path = _PLOG_DIR / "adoptions.csv"
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp_utc",
                "strategy",
                "reason",
                "decision_id",
                "dest_path",
                "committed",
                "git_tag",
                # 追記フィールド
                "policy_ok",
                "policy_reason",
                "forced",
                "win_rate",
                "max_drawdown",
                "trades",
                "evaluated_at",
                "policy_source",
            ],
        )
        if write_header:
            w.writeheader()
        w.writerow(
            {
                "timestamp_utc": ts,
                "strategy": strategy,
                "reason": reason,
                "decision_id": decision_id,
                "dest_path": str(dst.relative_to(PROJECT_ROOT)),
                "committed": committed,
                "git_tag": tag_applied,
                "policy_ok": policy_ok,
                "policy_reason": policy_reason,
                "forced": force_final,
                "win_rate": met["win_rate"],
                "max_drawdown": met["max_drawdown"],
                "trades": met["trades"],
                "evaluated_at": met["last_evaluated_at"],
                "policy_source": (policy_snapshot.get("source", {}) if isinstance(policy_snapshot, dict) else {}),
            }
        )

    return ActResult(
        True,
        "adopted",
        strategy,
        committed,
        tag_applied,
        dst,
        {
            "dst_rel": str(dst.relative_to(PROJECT_ROOT)),
            "policy_ok": policy_ok,
            "policy_reason": policy_reason,
            "forced": force_final,
            "metrics": met,
            **({"git_info": git_info} if git_info else {}),
        },
    )
