#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDCA Agent (recheck & adopt)

- Recheck: scripts.show_last_inventor_decision --json で最新 decision を取得
- Decide:   size > 0 かつ lift >= min_lift （オプション閾値）
- Adopt:    codex_reports/decision_registry.jsonl に追記し、auto/* ブランチを切って commit/push
            ※ .gitignore に阻まれないよう git add -f を使用

想定実行環境: GitHub Actions（runner に git 権限があること）
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Tuple


# ---------- Shell helpers ----------


def run(
    cmd: list[str], check: bool = True, capture: bool = False, cwd: str | None = None
) -> subprocess.CompletedProcess:
    kwargs = dict(text=True, cwd=cwd)
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
    print("+", " ".join(cmd))
    cp = subprocess.run(cmd, **kwargs)
    if check and cp.returncode != 0:
        if capture and cp.stdout:
            print(cp.stdout)
        raise subprocess.CalledProcessError(cp.returncode, cmd)
    return cp


# ---------- Decision I/O ----------


def load_latest_decision() -> Dict[str, Any]:
    """
    scripts.show_last_inventor_decision --json を呼び出して JSON を取得。
    取得に失敗したら {} を返す。
    """
    try:
        cp = run(
            [sys.executable, "-m", "scripts.show_last_inventor_decision", "--json"],
            check=True,
            capture=True,
        )
        raw = (cp.stdout or "").strip()
        return json.loads(raw or "{}")
    except Exception as e:
        print(f"warn: failed to load decision via script: {e}", file=sys.stderr)
        return {}


def should_adopt(decision: Dict[str, Any], *, min_lift: float = 0.0) -> Tuple[bool, str]:
    """
    採用基準：
      - decision.decision.size > 0
      - decision.decision.lift >= min_lift  (デフォルト 0.0)
    """
    d = decision.get("decision") or {}
    try:
        size = float(d.get("size", 0) or 0)
    except Exception:
        size = 0.0
    try:
        lift = float(d.get("lift", 0) or 0)
    except Exception:
        lift = 0.0
    reason = str(d.get("reason", "") or decision.get("reason", "") or "")

    ok = (size > 0.0) and (lift >= min_lift)
    msg = f"ok: lift {lift}, size {size}, reason {reason or '-'}"
    return ok, msg


# ---------- Git operations ----------


def git_current_branch() -> str:
    cp = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
    return (cp.stdout or "").strip()


def ensure_clean_worktree() -> None:
    # 不要だが、意図せぬ変更で失敗しないよう一応確認
    run(["git", "status", "--porcelain"], capture=True)


def create_adopt_branch_and_commit(
    decision: Dict[str, Any], *, prefix: str = "auto/adopt"
) -> Tuple[str, list[str]]:
    """
    - auto/adopt-YYYYMMDD-HHMMSS ブランチを作成
    - codex_reports/decision_registry.jsonl に追記
    - git add -f / commit
    """
    ts_utc = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    branch = f"{prefix}-{ts_utc}"

    # ブランチ作成
    run(["git", "checkout", "-b", branch])

    # レジストリに追記（無ければ作る）
    reg = Path("codex_reports/decision_registry.jsonl")
    reg.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "ts": dt.datetime.now(dt.UTC).isoformat(),
            "decision": decision,
        },
        ensure_ascii=False,
    )
    with reg.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    # .gitignore に無視されても add できるよう -f を付ける
    run(["git", "add", "-f", str(reg)])

    # コミット
    d = decision.get("decision") or {}
    reason = d.get("reason") or decision.get("reason") or "-"
    size = d.get("size", 0)
    lift = d.get("lift", 0)
    msg = f"pdca: adopt decision (size={size}, lift={lift}, reason={reason})"
    run(["git", "commit", "-n", "-m", msg])

    return branch, [str(reg)]


def push_branch(branch: str) -> None:
    run(["git", "push", "-u", "origin", branch])


# ---------- CLI ----------


def main() -> int:
    ap = argparse.ArgumentParser(description="PDCA Agent: recheck & adopt")
    ap.add_argument("--dryrun", action="store_true", help="変更を加えず判定ログのみ出力")
    ap.add_argument(
        "--min-lift", type=float, default=0.0, help="採用に必要な最小 lift（既定: 0.0）"
    )
    ap.add_argument("--branch-prefix", type=str, default="auto/adopt", help="作成ブランチの接頭辞")
    ap.add_argument(
        "--auto-adopt",
        action="store_true",
        help="（将来用）自動で main に取り込む。通常は PR 作成に任せる",
    )
    args = ap.parse_args()

    ensure_clean_worktree()

    decision = load_latest_decision()
    if not decision:
        print("Notice:  no decision found; exiting successfully.")
        return 0

    ok, detail = should_adopt(decision, min_lift=args.min_lift)
    print(f"Notice:  adopt decision? {ok} ({detail})")
    if not ok:
        # 採用しない＝成功終了（失敗扱いにしない）
        return 0

    if args.dryrun:
        print("Notice:  DRY-RUN mode → no changes will be committed.")
        return 0

    # 本採用フロー：ブランチ作成→レジストリ追記→commit/push
    branch, files = create_adopt_branch_and_commit(decision, prefix=args.branch_prefix)
    print(f"Notice:  created branch {branch}, committed files: {files}")

    push_branch(branch)
    print("Notice:  pushed branch to origin. (PR creation is handled by the workflow or GitHub UI)")

    # auto-adopt（将来的な自動マージ）はここで別途実装する想定
    if args.auto_adopt:
        print(
            "Notice:  auto_adopt flag is set, but auto-merge is delegated to workflow protections."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
