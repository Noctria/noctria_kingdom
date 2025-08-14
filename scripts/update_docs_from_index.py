#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_docs_from_index.py

📚 目的
- docs/00_index/00-INDEX.md を起点に、リンクされた Markdown 文書を走査
- 各ドキュメントに対し、「そのドキュメントの最終更新以降」の Git 変更（=最新の開発内容）を収集
- 収集結果を任意ログ（デフォルト: docs/_generated/update_docs.log）に出力
- 各ドキュメントに自動で CHANGELOG セクションを挿入/更新（マーカーで管理）
- 変更があれば git add/commit/push（--dry-run なら実ファイルは変更せず、push もしない）

📝 前提
- リポジトリ直下で実行すること（カレントが /mnt/d/noctria_kingdom）
- Git が使えること（コミット履歴があること）
- remote ‘origin’ が正しく設定済みで、push できること

🔧 使い方
  # ドライラン（差分抽出とログ出力のみ。ファイル変更・pushしない）
  python3 scripts/update_docs_from_index.py \
    --index docs/00_index/00-INDEX.md \
    --dry-run

  # 実更新 ＋ 自動コミット＆push
  python3 scripts/update_docs_from_index.py \
    --index docs/00_index/00-INDEX.md
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

# -----------------------------
# Config
# -----------------------------
AUTOGEN_BEGIN = "<!-- AUTOGEN:CHANGELOG START -->"
AUTOGEN_END = "<!-- AUTOGEN:CHANGELOG END -->"
DEFAULT_LOG = "docs/_generated/update_docs.log"
DEFAULT_BRANCH = None  # None=現在のブランチ
DOC_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")  # [Title](path/to/file.md)

# 変更抽出の対象（ソース側パスの大枠）
DIFF_SCOPE_DIRS = [
    "src",
    "noctria_gui",
    "airflow_docker",
    "experts",
    "tools",
    "scripts",
    # "docs" は除外（ドキュメント相互の更新ノイズを避ける）
]


@dataclass
class CommitInfo:
    short_hash: str
    author: str
    date_iso: str
    subject: str
    files: List[str]


# -----------------------------
# Utils
# -----------------------------
def sh(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)


def git_available() -> bool:
    try:
        sh(["git", "--version"], check=True)
        return True
    except Exception:
        return False


def git_root() -> Path:
    out = sh(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    return Path(out)


def current_branch() -> str:
    out = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    return out


def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def parse_index(index_path: Path) -> List[Path]:
    text = index_path.read_text(encoding="utf-8")
    paths = []
    for m in DOC_LINK_RE.finditer(text):
        rel = m.group(1).strip()
        # アンカー除去 e.g. file.md#section
        rel = rel.split("#", 1)[0]
        paths.append((index_path.parent / rel).resolve())
    # 重複除去・存在チェックは後段で
    return paths


def doc_last_update_ts(repo: Path, path: Path) -> Optional[int]:
    """
    ドキュメント自身を最後に更新したコミットのUnix epoch（秒）。
    ない場合は None（未コミット or 追跡外）。
    """
    try:
        out = sh(["git", "log", "-1", "--format=%ct", "--", str(path)], cwd=repo).stdout.strip()
        return int(out) if out else None
    except Exception:
        return None


def collect_commits_since(repo: Path, since_epoch: Optional[int]) -> List[CommitInfo]:
    """
    since_epoch 以降のコミットを対象に、ソース側のディレクトリ（DIFF_SCOPE_DIRS）の変更のみを拾う。
    docs/ 以下は除外。
    """
    if since_epoch is None:
        # ドキュメントが未コミットの場合は直近30日の変更を対象にする（安全側）
        since_opt = "--since=30.days"
    else:
        dt = datetime.fromtimestamp(since_epoch, tz=timezone.utc).isoformat()
        since_opt = f"--since={dt}"

    # --name-only で変更ファイル一覧を取る
    cmd = [
        "git", "log",
        "--pretty=%h|%an|%aI|%s",
        "--name-only",
        since_opt,
        "--",
    ] + DIFF_SCOPE_DIRS

    cp = sh(cmd, cwd=repo, check=False)  # 空でもOK
    lines = cp.stdout.splitlines()

    commits: List[CommitInfo] = []
    cur: Optional[CommitInfo] = None
    for line in lines:
        if not line.strip():
            continue
        if "|" in line and re.match(r"^[0-9a-f]{7,}", line):
            # 新しいコミット行
            hh, author, date_iso, subject = line.split("|", 3)
            if cur:
                commits.append(cur)
            cur = CommitInfo(short_hash=hh, author=author, date_iso=date_iso, subject=subject, files=[])
        else:
            # ファイル行
            if cur is not None:
                f = line.strip()
                # docs/ を除外（ドキュメント同士の更新は差分扱いしない）
                if f and not f.startswith("docs/"):
                    cur.files.append(f)
    if cur:
        commits.append(cur)

    # 変更ファイルが0のコミットはノイズなので除外
    commits = [c for c in commits if c.files]
    return commits


def build_changelog_section(doc_path: Path, commits: List[CommitInfo], last_ts: Optional[int]) -> str:
    title_date = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if last_ts else "N/A"
    lines = []
    lines.append(AUTOGEN_BEGIN)
    lines.append("")
    lines.append(f"### 🛠 Updates since: `{title_date}`")
    if not commits:
        lines.append("")
        lines.append("> （この期間に反映すべき開発差分は検出されませんでした）")
    else:
        lines.append("")
        for c in commits:
            # コミット概要
            lines.append(f"- `{c.short_hash}` {c.date_iso} — **{c.subject}** _(by {c.author})_")
            # 影響ファイル（長すぎないよう先頭10のみ表示）
            if c.files:
                show = c.files[:10]
                more = len(c.files) - len(show)
                for f in show:
                    lines.append(f"  - `{f}`")
                if more > 0:
                    lines.append(f"  - …and {more} more files")
    lines.append("")
    lines.append(AUTOGEN_END)
    lines.append("")
    return "\n".join(lines)


def splice_autogen_section(orig_text: str, new_section: str) -> str:
    """
    既存の AUTOGEN セクションを置換。無ければ末尾に追加。
    """
    begin = re.escape(AUTOGEN_BEGIN)
    end = re.escape(AUTOGEN_END)
    pat = re.compile(begin + r".*?" + end, re.DOTALL)

    if pat.search(orig_text):
        return pat.sub(new_section.strip(), orig_text)
    else:
        # 末尾に追記（前後に空行）
        if not orig_text.endswith("\n"):
            orig_text += "\n"
        return orig_text + "\n" + new_section


def git_add_commit_push(repo: Path, paths: List[Path], dry_run: bool, commit_msg: str, branch: Optional[str]) -> None:
    if dry_run:
        print("[DRY-RUN] skip git add/commit/push")
        return
    rels = [str(p.relative_to(repo)) for p in paths]
    if not rels:
        print("No changed files to commit.")
        return
    sh(["git", "add"] + rels, cwd=repo)
    # 変更が無ければ commit しない
    diff = sh(["git", "diff", "--cached", "--name-only"], cwd=repo).stdout.strip()
    if not diff:
        print("No staged changes; skip commit.")
        return
    sh(["git", "commit", "-m", commit_msg], cwd=repo)
    # push
    if branch is None:
        branch = current_branch()
    print(f"Pushing to origin/{branch} ...")
    sh(["git", "push", "origin", branch], cwd=repo)


# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Update docs pointed by 00-INDEX.md based on latest dev diffs (git).")
    ap.add_argument("--index", required=True, help="Path to 00-INDEX.md (e.g., docs/00_index/00-INDEX.md)")
    ap.add_argument("--log-out", default=DEFAULT_LOG, help=f"Path to output log file (default: {DEFAULT_LOG})")
    ap.add_argument("--branch", default=DEFAULT_BRANCH, help="Target branch to push (default: current branch)")
    ap.add_argument("--dry-run", action="store_true", help="Do not modify files or push; only print & write log")
    args = ap.parse_args()

    if not git_available():
        print("ERROR: git is not available in PATH.", file=sys.stderr)
        sys.exit(2)

    repo = git_root()
    index_path = (repo / args.index).resolve()
    if not index_path.exists():
        print(f"ERROR: index markdown not found: {index_path}", file=sys.stderr)
        sys.exit(2)

    print(f"Repo: {repo}")
    print(f"Index: {index_path}")

    # 対象ドキュメント一覧の抽出
    doc_paths = parse_index(index_path)
    # 重複・存在フィルタ
    uniq_docs = []
    seen = set()
    for p in doc_paths:
        if p in seen:
            continue
        seen.add(p)
        # 未存在でも、将来のために作るか？ → ここでは存在するもののみ対象に（安全）
        if p.exists():
            uniq_docs.append(p)
        else:
            print(f"WARNING: linked doc not found (skip): {p}")

    if not uniq_docs:
        print("No linked docs found from index. Nothing to do.")
        return

    # ログの用意
    log_path = (repo / args.log_out).resolve()
    ensure_parent(log_path)

    changed_docs: List[Path] = []
    with log_path.open("w", encoding="utf-8") as lf:
        lf.write(f"# Auto Doc Update Log\n\n")
        lf.write(f"- index: `{index_path.relative_to(repo)}`\n")
        lf.write(f"- generated_at: {datetime.now(timezone.utc).isoformat()}\n")
        lf.write(f"- dry_run: {args.dry_run}\n\n")

        for doc in uniq_docs:
            rel = doc.relative_to(repo)
            print(f"\n==> {rel}")
            lf.write(f"\n## {rel}\n")

            last_ts = doc_last_update_ts(repo, doc)
            if last_ts:
                lf.write(f"- last_doc_update: {datetime.fromtimestamp(last_ts, tz=timezone.utc).isoformat()}\n")
            else:
                lf.write(f"- last_doc_update: N/A (untracked or no commits)\n")

            commits = collect_commits_since(repo, last_ts)
            lf.write(f"- commits_found: {len(commits)}\n\n")

            # ログ詳細
            if not commits:
                lf.write("> No relevant commits since last doc update.\n")
            else:
                for c in commits:
                    lf.write(f"- {c.short_hash} {c.date_iso} — {c.subject} (by {c.author})\n")
                    for f in c.files[:10]:
                        lf.write(f"  - {f}\n")
                    if len(c.files) > 10:
                        lf.write(f"  - …and {len(c.files)-10} more files\n")

            # ドキュメント更新
            try:
                orig = doc.read_text(encoding="utf-8")
            except Exception:
                print(f"ERROR: cannot read doc: {doc}")
                lf.write(f"\n! ERROR: cannot read doc.\n")
                continue

            new_sec = build_changelog_section(doc, commits, last_ts)
            updated = splice_autogen_section(orig, new_sec)

            if updated != orig:
                lf.write("\n- action: would_update AUTOGEN section\n")
                if not args.dry_run:
                    doc.write_text(updated, encoding="utf-8")
                    changed_docs.append(doc)
                    print("   updated.")
                else:
                    print("   (dry-run) changes detected (not written).")
            else:
                lf.write("\n- action: no changes\n")
                print("   no changes.")

    print(f"\nLog written: {log_path.relative_to(repo)}")

    # Git 反映
    if changed_docs:
        print(f"\nChanged docs: {len(changed_docs)}")
        git_add_commit_push(
            repo=repo,
            paths=[log_path] + changed_docs,
            dry_run=args.dry_run,
            commit_msg="docs: auto-update from 00-INDEX (AUTOGEN changelog)",
            branch=args.branch,
        )
    else:
        # ログだけコミットしても良いが、ノイズになるのでスキップ
        print("No doc content changes; skip git commit/push (log not committed).")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
            print(f"\nCommand failed: {' '.join(e.cmd)}", file=sys.stderr)
            print(e.stderr or e.stdout, file=sys.stderr)
            sys.exit(e.returncode)
