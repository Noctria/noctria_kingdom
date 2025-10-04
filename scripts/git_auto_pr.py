#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, os, subprocess, sys, shutil, datetime as dt
from pathlib import Path

def sh(args, cwd=".", check=True, text=True):
    return subprocess.run(args, cwd=cwd, text=text, capture_output=True, check=check)

def have_gh() -> bool:
    return shutil.which("gh") is not None

def ensure_clean_index():
    # 生成物以外の変更があるときは注意喚起のみ（処理は続行）
    r = sh(["git","status","--porcelain"], check=False)
    dirty = [l for l in r.stdout.splitlines() if l.strip()]
    return dirty

def next_branch_name(prefix: str):
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{prefix}{ts}"
    return base  # 衝突回避（時刻ベースで十分ユニーク）

def has_changes(paths: list[str]) -> bool:
    """対象パスに差分があるかを確認"""
    try:
        r = subprocess.run(
            ["git", "diff", "--quiet", "--"] + paths,
            text=True,
        )
        return r.returncode != 0  # 0=差分なし, 1=差分あり
    except Exception:
        return True  # チェック不能時は強制Trueで処理続行

def main():
    ap = argparse.ArgumentParser(description="Create a branch, commit generated weekly, push, and (optionally) open a PR via gh CLI.")
    ap.add_argument("--files", nargs="+", required=True, help="files to add/commit (space separated)")
    ap.add_argument("--branch-prefix", default="chore/weekly-report-", help="branch name prefix")
    ap.add_argument("--title", default="chore: weekly report update", help="PR title")
    ap.add_argument("--body-path", default="docs/_generated/weekly_insert.md", help="PR body path (used if gh is available)")
    ap.add_argument("--remote", default="origin", help="git remote (default: origin)")
    ap.add_argument("--base", default="main", help="base branch to target PR against")
    args = ap.parse_args()

    # --- 差分チェック（追加） ---
    if not has_changes(args.files):
        print("ℹ️ No changes detected in target files → skipping PR")
        return 0

    # 1) ブランチ作成
    branch = next_branch_name(args.branch_prefix)
    sh(["git", "fetch", args.remote, args.base], check=False)
    sh(["git", "checkout", args.base], check=False)
    sh(["git", "checkout", "-b", branch], check=True)

    # 2) ファイル存在チェック＆ add
    to_add = []
    for f in args.files:
        p = Path(f)
        if p.exists():
            to_add.append(f)
    if not to_add:
        print("No target files exist. Nothing to commit.")
        return 0

    sh(["git","add"] + to_add, check=True)
    msg = f"{args.title}"
    sh(["git","commit","-m", msg], check=True)

    # 3) push
    sh(["git","push","-u", args.remote, branch], check=True)

    # 4) PR（gh があれば）
    pr_url = None
    if have_gh():
        body_arg = []
        if Path(args.body_path).exists():
            body_arg = ["-F", args.body_path]
        r = sh(
            ["gh","pr","create","--fill","--title", args.title, "--base", args.base, "--head", branch] 
            + (body_arg if body_arg else []),
            check=False
        )
        out = (r.stdout or "") + (r.stderr or "")
        for line in out.splitlines():
            if line.strip().startswith("https://github.com/"):
                pr_url = line.strip()
                break

    # 5) 成果をJSONで返す（agent_runnerがパースしやすいように）
    print({"branch": branch, "pushed": True, "pr_url": pr_url or ""})

if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.stderr or "")
        print({"error": True, "returncode": e.returncode})
        sys.exit(e.returncode)
