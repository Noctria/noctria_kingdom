#!/usr/bin/env python3
# coding: utf-8
"""
update_docs_from_index.py
────────────────────────────────────────────────────────────
00-INDEX.md と、その中でリンクされている Markdown（想定21本）を走査し、
各ドキュメントの「最終更新以降」のGitログを集計して変更サマリを作成。
サマリは以下の2系統で出力します。

  1) 任意のログ（docs/_build/logs/... に集約ログと各ファイル個別ログ）
  2) 各ドキュメントへの自動追記（「## Update Log (auto)」節として追記）

最後に、--apply 指定時はファイルを上書き保存、
--push 指定時は git add/commit/push まで自動実行します。

“関連するコード範囲”の推定は次の順で行います:
  a) ドキュメント本文中の `src/...` や `noctria_gui/...` にマッチする相対パスを抽出し、そこを対象に git log
  b) 抽出できない場合は、一般的に文書の範囲になることが多い top-level を対象:
     ["src", "noctria_gui", "airflow_docker", "docs"]

要件:
  - リポジトリ直下で実行（または --repo-root 指定）
  - Git が使える環境（リモート origin 設定済み）
  - Python 3.9+

例:
  python tools/update_docs_from_index.py \
    --index docs/00-INDEX.md \
    --since auto \
    --apply --push

まずは dry-run:
  python tools/update_docs_from_index.py --index docs/00-INDEX.md --dry-run
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
from typing import List, Dict, Optional, Tuple

# ---------------------------
# Utils
# ---------------------------

RE_MD_LINK = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
RE_CODE_PATH = re.compile(r'(?P<p>(?:src|noctria_gui|airflow_docker|docs)/[A-Za-z0-9_\-./]+)')

TOP_LEVEL_DEFAULTS = ["src", "noctria_gui", "airflow_docker", "docs"]

@dataclass
class DocTarget:
    path: Path
    related_paths: List[str]  # for git log scoping
    since_iso: str            # ISO string used for git --since
    last_mtime: datetime      # filesystem last modified time

@dataclass
class CommitEntry:
    hash: str
    date: str   # iso
    author: str
    subject: str

def sh(cmd: List[str], cwd: Optional[Path]=None, check: bool=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=check)

def git_root(explicit: Optional[Path]) -> Path:
    if explicit:
        return explicit.resolve()
    try:
        out = sh(["git", "rev-parse", "--show-toplevel"], check=True)
        return Path(out.stdout.strip()).resolve()
    except subprocess.CalledProcessError:
        print("ERROR: Not a git repository (or git not found). Use --repo-root.", file=sys.stderr)
        sys.exit(2)

def parse_index(index_md: Path) -> List[Path]:
    text = index_md.read_text(encoding="utf-8", errors="ignore")
    links = []
    for m in RE_MD_LINK.finditer(text):
        href = m.group(1).strip()
        # 画像や外部URLは除外
        if href.startswith("http://") or href.startswith("https://") or href.startswith("mailto:"):
            continue
        if any(href.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg"]):
            continue
        p = (index_md.parent / href).resolve()
        if p.suffix.lower() == ".md" and p.exists():
            links.append(p)
    # index 自体も先頭に含める
    if index_md.suffix.lower() == ".md":
        links = [index_md.resolve()] + [p for p in links if p.resolve() != index_md.resolve()]
    # 重複排除
    uniq = []
    seen = set()
    for p in links:
        rp = str(p)
        if rp not in seen:
            uniq.append(p)
            seen.add(rp)
    return uniq

def find_related_paths(md_path: Path) -> List[str]:
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    found = set()
    for m in RE_CODE_PATH.finditer(text):
        rel = m.group("p")
        # 末尾の句読点や括弧を落とす
        rel = rel.strip().rstrip(").,;]}")
        if Path(rel).exists():
            found.add(rel)
    if found:
        return sorted(found)
    return TOP_LEVEL_DEFAULTS[:]  # fallback

def file_mtime(p: Path) -> datetime:
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)

def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()

def choose_since(since_arg: str, mtime: datetime) -> str:
    """
    --since の解釈:
      - "auto"  : ドキュメントの最終更新時刻 (ファイル mtime) を使用
      - それ以外: git の --since へそのまま渡す（"2025-08-01", "2 weeks ago" 等）
    """
    if since_arg == "auto":
        return iso(mtime)
    return since_arg

def git_log(repo: Path, since_iso: str, paths: List[str]) -> List[CommitEntry]:
    # pretty: <hash>|<date>|<author>|<subject>
    fmt = "%h|%ad|%an|%s"
    cmd = ["git", "log", f"--since={since_iso}", f"--pretty=format:{fmt}", "--date=iso"]
    cmd += ["--"] + paths
    try:
        cp = sh(cmd, cwd=repo, check=True)
        lines = [ln for ln in cp.stdout.splitlines() if ln.strip()]
        out: List[CommitEntry] = []
        for ln in lines:
            parts = ln.split("|", 3)
            if len(parts) == 4:
                out.append(CommitEntry(hash=parts[0], date=parts[1], author=parts[2], subject=parts[3]))
        return out
    except subprocess.CalledProcessError as e:
        # パスが1つも該当しない場合などは空扱い
        return []

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

def append_update_section(md_path: Path, commits: List[CommitEntry], dry_run: bool) -> Tuple[bool, str]:
    """
    ドキュメント末尾に以下の形式で追記する:
      ## Update Log (auto)
      - 2025-08-15 12:34  (abc123) subject  — author
      ...
    すでに同日同内容が入っている場合は重複追記しない簡易チェック付き。
    """
    if not commits:
        return False, "no commits"

    head = "## Update Log (auto)"
    lines = md_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    # 今日追加分として生成
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    block = [head, f"", f"**Synced at (UTC)**: {today}", ""]
    for c in commits:
        # ISO → "YYYY-MM-DD HH:MM"
        when = c.date.replace("T", " ")[:16]
        block.append(f"- {when}  ({c.hash}) {c.subject}  — {c.author}")
    block_text = "\n".join(block) + "\n"

    existing_text = "\n".join(lines)
    # 簡易重複チェック：同じhash行が既に含まれていれば追記しない
    if any(c.hash in existing_text for c in commits):
        return False, "already contains some of these commits"

    new_text = existing_text
    if head in existing_text:
        # 既存の Update Log の前に1空行挿入して追記
        new_text = existing_text + "\n\n" + block_text
    else:
        new_text = existing_text.rstrip() + "\n\n" + block_text

    if not dry_run:
        md_path.write_text(new_text, encoding="utf-8")

    return True, f"appended {len(commits)} entries"

def git_add_commit_push(repo: Path, message: str, push: bool) -> None:
    # add
    sh(["git", "add", "docs"], cwd=repo, check=True)
    # commit（変更がなければスキップ）
    try:
        sh(["git", "commit", "-m", message], cwd=repo, check=True)
        if push:
            # リモートは origin、現在ブランチへプッシュ
            sh(["git", "push"], cwd=repo, check=True)
    except subprocess.CalledProcessError as e:
        # 何も変更がないケース
        print("No changes to commit.", file=sys.stderr)

# ---------------------------
# Main
# ---------------------------

def main():
    ap = argparse.ArgumentParser(description="Update docs listed in 00-INDEX.md based on recent git changes.")
    ap.add_argument("--index", default="docs/00-INDEX.md", help="Path to 00-INDEX.md")
    ap.add_argument("--repo-root", default=None, help="Repository root (if not running inside git repo)")
    ap.add_argument("--since", default="auto", help='Since boundary for git log. "auto" = per-file mtime; or pass "2025-08-01", "2 weeks ago".')
    ap.add_argument("--apply", action="store_true", help="Actually modify markdown files (append Update Log).")
    ap.add_argument("--push", action="store_true", help="After apply, git add/commit/push.")
    ap.add_argument("--dry-run", action="store_true", help="Do not write files or push. Just log.")
    ap.add_argument("--log-dir", default="docs/_build/logs", help="Directory to write logs into.")
    args = ap.parse_args()

    repo = git_root(Path(args.repo_root) if args.repo_root else None)
    index_md = (repo / args.index).resolve()
    if not index_md.exists():
        print(f"ERROR: index not found: {index_md}", file=sys.stderr)
        sys.exit(2)

    # 1) 対象ファイルを列挙
    docs = parse_index(index_md)
    if not docs:
        print("No markdown files found via index.", file=sys.stderr)
        sys.exit(1)

    # 2) ログ出力先
    log_dir = (repo / args.log_dir).resolve()
    ensure_dir(log_dir)
    batch_stamp = now_stamp()
    batch_log = log_dir / f"changes_{batch_stamp}.log"

    batch_lines = []
    batch_lines.append(f"# Doc Update Scan @ {datetime.now(timezone.utc).isoformat()}Z")
    batch_lines.append(f"Repo: {repo}")
    batch_lines.append(f"Index: {index_md}")
    batch_lines.append("")

    # 3) 各ドキュメントごとに git log を収集
    changed_any = False
    for md in docs:
        mtime = file_mtime(md)
        since_iso = choose_since(args.since, mtime)
        related = find_related_paths(md)
        commits = git_log(repo, since_iso, related)
        batch_lines.append(f"## {md.relative_to(repo)}")
        batch_lines.append(f"- since: {since_iso}")
        batch_lines.append(f"- related_paths: {', '.join(related)}")
        batch_lines.append(f"- commits: {len(commits)}")
        for c in commits:
            batch_lines.append(f"  - {c.date} {c.hash} {c.author}: {c.subject}")
        batch_lines.append("")

        # 個別ログ
        per_log = log_dir / f"{md.stem}_changes_{batch_stamp}.log"
        per_text = "\n".join(batch_lines[-(len(commits)+4):])  # そのセクションだけ
        per_log.write_text(per_text, encoding="utf-8")

        # ドキュメントへ追記（apply時のみ）
        if args.apply and commits:
            ok, msg = append_update_section(md, commits, dry_run=args.dry_run)
            batch_lines.append(f"- apply: {ok} ({msg})")
            if ok:
                changed_any = True
        else:
            batch_lines.append("- apply: skipped")
        batch_lines.append("")

    # 4) バッチログを書き出し
    batch_log.write_text("\n".join(batch_lines) + "\n", encoding="utf-8")
    print(f"[LOG] Wrote batch log: {batch_log}")

    # 5) git push
    if args.apply and not args.dry_run:
        if changed_any:
            msg = f"docs: auto-append Update Log from git since ({args.since}) @ {batch_stamp}"
            git_add_commit_push(repo, msg, push=args.push)
            print("[GIT] commit/push completed.")
        else:
            print("[GIT] no changes to commit/push.")
    else:
        print("[GIT] skipped (apply/dry-run flags).")

if __name__ == "__main__":
    main()
