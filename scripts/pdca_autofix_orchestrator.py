# scripts/pdca_autofix_orchestrator.py
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable or "python"

PDCA = ROOT / "scripts" / "run_pdca_agents.py"
AUTOFIX = ROOT / "scripts" / "auto_fix_loop.py"
LATEST_CYCLE_MD = ROOT / "src" / "codex_reports" / "latest_codex_cycle.md"

# GREEN 判定
GREEN_PAT = re.compile(r"^\s*-\s*GREEN:\s*(True|true|1)", re.M)
RESULT_LINE_PAT = re.compile(r"\[result\]\s*(✅ GREEN|⚠️ NOT GREEN)")


# =========================
# DB（agent_logs）ユーティリティ
# =========================
def _db_path() -> Path:
    # run_pdca_agents.py と同じ既定に揃える
    return Path(os.getenv("NOCTRIA_PDCA_DB", str(ROOT / "src" / "codex_reports" / "pdca_log.db")))


def _db_connect() -> Optional[sqlite3.Connection]:
    try:
        dbp = _db_path()
        dbp.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(dbp)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                role TEXT,
                title TEXT,
                content TEXT,
                created_at TEXT
            );
            """
        )
        return conn
    except Exception:
        return None


def _log_agent(role: str, title: str, content: str, trace_id: str) -> None:
    conn = _db_connect()
    if not conn:
        return
    try:
        jst = timezone(timedelta(hours=9))
        ts = datetime.now(tz=jst).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO agent_logs (trace_id, role, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (trace_id, role, title, content, ts),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =========================
# サブプロセス
# =========================
def run(cmd: list[str] | str, env: Optional[dict] = None) -> Tuple[int, str, str]:
    proc = subprocess.run(
        cmd if isinstance(cmd, list) else cmd,
        text=True,
        capture_output=True,
        shell=isinstance(cmd, str),
        cwd=str(ROOT),
        env=env,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def is_green_from_md(md_path: Path) -> bool:
    try:
        txt = md_path.read_text(encoding="utf-8")
    except Exception:
        return False
    m = GREEN_PAT.search(txt)
    return bool(m and m.group(1).lower() in {"true", "1"})


def run_pdca(branch: str | None = None, want_push: bool = False, trace_id: str = "") -> bool:
    args = [PY, str(PDCA)]
    if branch:
        args += ["--branch", branch]
    # push 指定は PDCA 側が環境変数で拾う
    env = os.environ.copy()
    if want_push:
        env["NOCTRIA_PDCA_GIT_PUSH"] = "1"

    rc, out, err = run(args, env=env)
    # ログを短縮して agent_logs へ
    tail = "\n".join((out + "\n" + err).splitlines()[-60:])
    _log_agent("orchestrator", "PDCA run (tail)", tail, trace_id)

    # 1) 画面出力の最終結果ラインで早取り
    if RESULT_LINE_PAT.search(out) or RESULT_LINE_PAT.search(err):
        return "[result] ✅ GREEN" in out or "[result] ✅ GREEN" in err
    # 2) 公式アーティファクトを読む（堅牢）
    return is_green_from_md(LATEST_CYCLE_MD)


def run_autofix(max_iters: int, trace_id: str = "") -> int:
    env = os.environ.copy()
    env.setdefault("NOCTRIA_AUTOFIX_PRECOMMIT", "1")  # pre-commit も実行
    env.setdefault("NOCTRIA_AUTOFIX_COMMIT", "1")  # 変更をコミット（既定）
    cmd = [PY, str(AUTOFIX), "--max-iters", str(max_iters)]
    rc, out, err = run(cmd, env=env)
    tail = "\n".join((out + "\n" + err).splitlines()[-120:])
    _log_agent("orchestrator", f"AutoFix exit={rc}", tail, trace_id)
    return rc


def wait_git_fs(delay: float = 0.5) -> None:
    """CIやFSの反映待ち（軽いウェイト）"""
    time.sleep(delay)


# =========================
# Main
# =========================
def main() -> int:
    ap = argparse.ArgumentParser(description="Orchestrate PDCA + AutoFix loop")
    ap.add_argument("--cycles", type=int, default=5, help="最大PDCA→AutoFixサイクル数")
    ap.add_argument(
        "--autofix-iters", type=int, default=3, help="AutoFixの1回当たりイテレーション上限"
    )
    ap.add_argument("--pdca-branch", default=os.getenv("NOCTRIA_PDCA_BRANCH", "dev/pdca-tested"))
    ap.add_argument(
        "--push", action="store_true", help="PDCAレポート用ブランチをpush（PDCA側の設定でも可）"
    )
    args = ap.parse_args()

    # オーケストレータの trace_id（JST）
    jst = timezone(timedelta(hours=9))
    orch_trace_id = f"orch_{datetime.now(tz=jst).strftime('%Y%m%d_%H%M%S')}"

    print(f"[orchestrator] start: cycles={args.cycles} autofix-iters={args.autofix_iters}")
    _log_agent(
        "orchestrator",
        "start",
        f"cycles={args.cycles}, autofix-iters={args.autofix_iters}",
        orch_trace_id,
    )

    # 1st PDCA
    print("[orchestrator] run PDCA (initial)")
    green = run_pdca(branch=args.pdca_branch, want_push=args.push, trace_id=orch_trace_id)
    if green:
        msg = "[orchestrator] ✅ GREEN at first PDCA. Done."
        print(msg)
        _log_agent("orchestrator", "GREEN", "first PDCA", orch_trace_id)
        return 0

    # cyclesループ
    for c in range(1, args.cycles + 1):
        print(f"\n[orchestrator] === Cycle {c} ===")
        _log_agent("orchestrator", f"cycle {c} begin", "", orch_trace_id)

        # AutoFix
        print(f"[orchestrator] run AutoFix (max-iters={args.autofix_iters})")
        rc = run_autofix(args.autofix_iters, trace_id=orch_trace_id)
        if rc != 0:
            print(f"[orchestrator] AutoFix exit code={rc} (続行)")
            _log_agent("orchestrator", f"cycle {c} AutoFix nonzero", f"rc={rc}", orch_trace_id)

        # 反映待ち＋再PDCA
        wait_git_fs()
        print("[orchestrator] run PDCA (after AutoFix)")
        green = run_pdca(branch=args.pdca_branch, want_push=args.push, trace_id=orch_trace_id)
        if green:
            print("[orchestrator] ✅ GREEN after cycle", c)
            _log_agent("orchestrator", "GREEN", f"after cycle {c}", orch_trace_id)
            return 0

    print("[orchestrator] 🛑 budget exceeded — still NOT GREEN.")
    _log_agent(
        "orchestrator", "NOT GREEN", f"budget exceeded after {args.cycles} cycles", orch_trace_id
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
