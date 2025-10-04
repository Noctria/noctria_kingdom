#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import shutil
import subprocess
import sys
import datetime as dt
from pathlib import Path
from typing import List


def sh(args: List[str], cwd: str = ".", check: bool = True, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, text=text, capture_output=True, check=check)


def have_gh() -> bool:
    return shutil.which("gh") is not None


def ensure_clean_index() -> list[str]:
    """生成物以外の変更があるときは注意喚起のみ（処理は続行）"""
    r = sh(["git", "status", "--porcelain"], check=False)
    dirty = [l for l in r.stdout.splitlines() if l.strip()]
    return dirty


def next_branch_name(prefix: str) -> str:
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}{ts}"


def has_changes_against(base_ref: str, paths: List[str]) -> bool:
    """
    base_ref（例: origin/main）と比較して paths 配下に差分があるか。
    - returncode 0: 差分なし, 1: 差分あり
    """
    try:
        r = subprocess.run(["git", "diff", "--quiet", base_ref, "--"] + paths, text=True)
        return r.returncode != 0
    except Exception:
        # 何かあれば保守的に True（差分あり扱い）
        return True


def changed_files_against(base_ref: str) -> list[str]:
    """base_ref と比較した変更ファイル一覧を返す"""
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", base_ref, "--"],
            text=True,
            capture_output=True,
            check=False,
        )
        return [p.strip() for p in r.stdout.splitlines() if p.strip()]
    except Exception:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Create a branch, commit generated files, push, and (optionally) open a PR via gh CLI."
    )
    ap.add_argument("--files", nargs="+", required=True, help="files to add/commit (space separated)")
    ap.add_argument("--branch-prefix", default="chore/weekly-report-", help="branch name prefix")
    ap.add_argument("--title", default="chore: weekly report update", help="PR title")
    ap.add_argument("--title-prefix", default="", help="Prefix to prepend to PR title (e.g. 'docs: ')")
    ap.add_argument("--body-path", default="docs/_generated/weekly_insert.md", help="PR body path (used if gh is available)")
    ap.add_argument("--remote", default="origin", help="git remote (default: origin)")
    ap.add_argument("--base", default="main", help="base branch to target PR against")
    ap.add_argument("--label", action="append", default=[], help="Labels to add to the PR (can specify multiple)")
    ap.add_argument("--reviewer", action="append", default=[], help="Reviewers to request (can specify multiple)")
    ap.add_argument("--assignee", action="append", default=[], help="Assignees to add (can specify multiple)")
    args = ap.parse_args()

    # 0) 対象ファイルの存在チェック（1つも無ければ終了）
    to_add = [f for f in args.files if Path(f).exists()]
    if not to_add:
        print("No target files exist. Nothing to commit.")
        print({"skipped": True, "reason": "no_target_files"})
        return 0

    # 1) ベース追従（失敗しても続行）
    sh(["git", "fetch", args.remote, args.base], check=False)
    base_ref = f"{args.remote}/{args.base}"

    # 2) base と比較して対象ファイルに差分が無ければスキップ
    if not has_changes_against(base_ref, to_add):
        msg = "ℹ️ No changes against base detected in target files → skipping PR"
        print(msg)
        print({"skipped": True, "reason": "no_changes_against_base", "base": base_ref})
        return 0

    # --- 変更検知で自動ラベル/レビュアー付与（戦略コードが含まれる場合） ---
    changed = changed_files_against(base_ref)
    if any(p.startswith("src/strategies/") for p in changed):
        if "strategies" not in args.label:
            args.label.append("strategies")
        if not args.reviewer:
            args.reviewer.extend(["alice", "bob"])
        print(
            "ℹ️  Detected changes under src/strategies/ → add label:[strategies], reviewers:[alice,bob]"
        )

    # 3) ブランチ作成
    branch = next_branch_name(args.branch_prefix)
    sh(["git", "checkout", args.base], check=False)
    sh(["git", "checkout", "-b", branch], check=True)

    # 4) add & commit
    sh(["git", "add"] + to_add, check=True)
    msg = f"{args.title}"
    rc = subprocess.run(["git", "diff", "--cached", "--quiet", "--"] + to_add).returncode
    if rc == 0:
        print("ℹ️ No staged changes → skipping commit & PR")
        print({"skipped": True, "reason": "no_staged_changes"})
        return 0

    sh(["git", "commit", "-m", msg], check=True)

    # 5) push
    sh(["git", "push", "-u", args.remote, branch], check=True)

    # 6) PR（gh があれば）
    pr_url = None
    if have_gh():
        final_title = f"{args.title_prefix}{args.title}".strip()
        gh_cmd = [
            "gh", "pr", "create",
            "--title", final_title,
            "--base", args.base,
            "--head", branch,
            "--fill",
        ]
        if Path(args.body_path).exists():
            gh_cmd += ["-F", args.body_path]
        for lbl in args.label:
            gh_cmd += ["--label", lbl]
        for rev in args.reviewer:
            gh_cmd += ["--reviewer", rev]
        for asg in args.assignee:
            gh_cmd += ["--assignee", asg]

        r = sh(gh_cmd, check=False)
        out = (r.stdout or "") + (r.stderr or "")
        for line in out.splitlines():
            s = line.strip()
            if s.startswith("https://github.com/"):
                pr_url = s
                break

    # 7) 成果をJSONで返す
    print({"branch": branch, "pushed": True, "pr_url": pr_url or ""})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.stderr or "")
        print({"error": True, "returncode": e.returncode})
        sys.exit(e.returncode)
