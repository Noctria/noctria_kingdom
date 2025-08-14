# src/core/act_service.py
#!/usr/bin/env python3
# coding: utf-8
"""
Act (Adopt) Service
- 評価済み戦略を正式採用としてプロジェクトに取り込むユーティリティ
- できれば Git へコミット/タグ付け（無ければフォールバックでファイルコピーのみ）
- 採用ログを CSV に記録
"""

from __future__ import annotations

import csv
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

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
        # repo 配下か確認
        r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return r.returncode == 0 and r.stdout.decode().strip() == "true"
    except Exception:
        return False


def _git_commit_and_tag(repo_dir: Path, rel_path: str, message: str, tag: Optional[str]) -> ActResult:
    committed = False
    try:
        subprocess.run(["git", "add", rel_path], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=repo_dir, check=True)
        committed = True
        if tag:
            subprocess.run(["git", "tag", tag], cwd=repo_dir, check=True)
        return ActResult(True, "Committed to git", "", True, tag, None, {})
    except subprocess.CalledProcessError as e:
        return ActResult(False, f"Git operation failed: {e}", "", committed, tag, None, {"returncode": e.returncode})


def adopt_strategy(strategy: str, *, reason: str = "", decision_id: Optional[str] = None, dry_run: bool = False) -> ActResult:
    """
    veritas_generated/{strategy}.py -> strategies/adopted/{strategy}.py へ採用。
    Git が使える場合は add/commit + tag まで。
    """
    src = _GEN_DIR / f"{strategy}.py"
    if not src.exists():
        return ActResult(False, f"source not found: {src}", strategy, False, None, None, {})

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dst = ADOPTED_DIR / f"{strategy}.py"

    commit_msg = f"adopt(strategy={strategy}) reason='{reason}' decision_id={decision_id or '-'} at {ts}"
    tag_name = f"adopted/{strategy}/{ts}"

    if dry_run:
        return ActResult(True, "[DRY-RUN] adoption simulated", strategy, False, tag_name, dst, {
            "src": str(src), "dst": str(dst), "commit_message": commit_msg
        })

    # 1) ファイルコピー（上書きOK）
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

    committed = False
    tag_applied: Optional[str] = None
    if _git_available(PROJECT_ROOT):
        r = _git_commit_and_tag(PROJECT_ROOT, str(dst.relative_to(PROJECT_ROOT)), commit_msg, tag_name)
        committed = r.ok and r.committed
        tag_applied = tag_name if r.ok else None

    # 2) 採用ログ CSV 追記
    log_path = _PLOG_DIR / "adoptions.csv"
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "timestamp_utc", "strategy", "reason", "decision_id", "dest_path", "committed", "git_tag"
        ])
        if write_header:
            w.writeheader()
        w.writerow({
            "timestamp_utc": ts,
            "strategy": strategy,
            "reason": reason,
            "decision_id": decision_id,
            "dest_path": str(dst.relative_to(PROJECT_ROOT)),
            "committed": committed,
            "git_tag": tag_applied,
        })

    return ActResult(True, "adopted", strategy, committed, tag_applied, dst, {"dst_rel": str(dst.relative_to(PROJECT_ROOT))})
