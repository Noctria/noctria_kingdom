#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_docs_from_index.py — AutoDoc v1.6 (file_content + hardening)

Markdown 内の AUTODOC ブロックを検出し、以下の2モードで本文を書き換える:
- mode=git_log      : Git のコミット履歴を整形して挿入（既定）
- mode=file_content : 指定ファイルの最新内容をそのまま挿入（コードフェンス対応）

【マーカー例】

(1) Gitログを差し込む:
<!-- AUTODOC:BEGIN path_globs=src/plan_data/*.py;src/plan_data/**/*.py limit=30 title="Plan Data の最近の変更" since=2025-08-01 author=Noctoria include_files=false -->
(ここは自動で置き換え)
<!-- AUTODOC:END -->

(2) Mermaidファイル内容を差し込む:
<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/architecture/diagrams/act_layer.mmd fence=mermaid title="Act Layer Mermaid図" -->
(ここは自動で置き換え)
<!-- AUTODOC:END -->

(3) 複数ファイルをまとめて差し込む（各ファイルで小見出し＋コードブロック化）:
<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/diagrams/*.mmd fence=mermaid title="最新Mermaid図セット" -->
(ここは自動で置き換え)
<!-- AUTODOC:END -->

実行例:
  python3 scripts/update_docs_from_index.py --docs-root docs --repo-root . --dry-run False

安全策:
- 既定で .bak バックアップを作成
- YAML front-matter の last_updated をJSTで自動更新（存在時のみ）
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import glob
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =============================
# 基本ユーティリティ
# =============================

def run_cmd(cmd: List[str], cwd: Optional[Path] = None) -> str:
    res = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
    return res.stdout

def is_git_repo(path: Path) -> bool:
    try:
        run_cmd(["git", "rev-parse", "--is-inside-work-tree"], cwd=path)
        return True
    except Exception:
        return False

def now_iso_jst() -> str:
    JST = dt.timezone(dt.timedelta(hours=9))
    return dt.datetime.now(JST).isoformat()

def parse_bool(val: Optional[str], default: bool = True) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")

# =============================
# マーカー解析
# =============================

BEGIN_RE = re.compile(r"<!--\s*AUTODOC:BEGIN(?P<attrs>[^>]*)-->", re.IGNORECASE)
END_RE   = re.compile(r"<!--\s*AUTODOC:END\s*-->", re.IGNORECASE)
ATTR_RE  = re.compile(r"([a-zA-Z_]+)\s*=\s*(\"[^\"]*\"|'[^']*'|[^ \t\r\n]+)")

@dataclasses.dataclass
class AutoDocBlock:
    start_span: Tuple[int, int]
    end_span: Tuple[int, int]
    attrs: Dict[str, str]
    body_span: Tuple[int, int]

def parse_attrs(attr_text: str) -> Dict[str, str]:
    attrs: Dict[str, str] = {}
    for m in ATTR_RE.finditer(attr_text or ""):
        key = m.group(1)
        val = m.group(2)
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        attrs[key] = val
    return attrs

def find_autodoc_blocks(md_text: str) -> List[AutoDocBlock]:
    blocks: List[AutoDocBlock] = []
    pos = 0
    while True:
        m_begin = BEGIN_RE.search(md_text, pos)
        if not m_begin:
            break
        m_end = END_RE.search(md_text, m_begin.end())
        if not m_end:
            # ENDがない場合はスキップ（壊れたブロックは無視）
            pos = m_begin.end()
            continue
        attrs = parse_attrs(m_begin.group("attrs"))
        body_start, body_end = m_begin.end(), m_end.start()
        blocks.append(
            AutoDocBlock(
                start_span=(m_begin.start(), m_begin.end()),
                end_span=(m_end.start(), m_end.end()),
                attrs=attrs,
                body_span=(body_start, body_end),
            )
        )
        pos = m_end.end()
    return blocks

# =============================
# Git ログ収集
# =============================

@dataclasses.dataclass
class CommitEntry:
    sha: str
    iso_time: str
    subject: str
    author: str
    files: List[str]

def git_log_for_paths(
    repo_root: Path,
    paths: List[str],
    limit: int = 50,
    since: Optional[str] = None,
    author: Optional[str] = None,
) -> List[CommitEntry]:
    """
    指定パス（複数）に関するコミット履歴を新しい順に取得。
    paths が空のときは安全のため空リストを返す（リポジトリ全体のログを拾わない）。
    """
    if not paths:
        return []

    pretty = "%H|%cI|%s|%an"
    cmd = ["git", "log", f"--pretty=format:{pretty}", f"-n{limit}"]
    if since:
        cmd.append(f"--since={since}")
    if author:
        cmd.append(f"--author={author}")
    cmd.append("--")
    cmd.extend(paths)

    out = run_cmd(cmd, cwd=repo_root)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    entries: List[CommitEntry] = []

    for ln in lines:
        parts = ln.split("|", 3)
        if len(parts) != 4:
            continue
        sha, iso_time, subject, author_name = parts
        files_out = run_cmd(["git", "show", "--name-only", "--pretty=format:", sha], cwd=repo_root)
        files = [f.strip() for f in files_out.splitlines() if f.strip()]
        entries.append(CommitEntry(sha=sha[:7], iso_time=iso_time, subject=subject, author=author_name, files=files))
    return entries

# =============================
# パス解決
# =============================

def resolve_globs(globs_text: str, repo_root: Path) -> List[str]:
    """
    'a/*.py;b/**/*.py' → 実ファイル相対パスへ解決。マッチなしのパターンはそのまま残す。
    出力順は安定化のため sort 済み。
    """
    results: List[str] = []
    for g in [p.strip() for p in (globs_text or "").split(";") if p.strip()]:
        matches = sorted(glob.glob(str(repo_root / g), recursive=True))
        if matches:
            for m in matches:
                rel = os.path.relpath(m, start=repo_root)
                results.append(rel)
        else:
            results.append(g)

    # unique（順序維持）
    seen = set()
    dedup = []
    for x in results:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup

# =============================
# レンダリング
# =============================

def render_git_section(
    title: Optional[str],
    entries: List[CommitEntry],
    include_files: bool = True
) -> str:
    lines: List[str] = []
    if title:
        lines += [f"### {title}", ""]
    if not entries:
        lines.append("_変更は見つかりませんでした。_")
        return "\n".join(lines)

    for e in entries:
        lines.append(f"- **{e.sha}** {e.iso_time} — {e.subject} (by {e.author})")
        if include_files and e.files:
            for f in e.files[:20]:  # ノイズ抑制
                lines.append(f"  - `{f}`")
    return "\n".join(lines)

def read_text_safely(path: Path, max_bytes: int = 2_000_000) -> str:
    size = path.stat().st_size
    if size > max_bytes:
        return f"<!-- Skipped: {path.name} is too large ({size} bytes) -->"
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"<!-- Skipped: {path.name} is not UTF-8 text -->"

def render_file_contents_section(
    repo_root: Path,
    title: Optional[str],
    rel_paths: List[str],
    fence: Optional[str] = None,
) -> str:
    """
    指定ファイル群の内容をまとめて差し込む。
    - title があればセクション見出し
    - 複数ファイル時: 各ファイルを小見出し(####)＋コードブロックで列挙
    - fence があれば ```{fence} でコードフェンス化
    """
    lines: List[str] = []
    if title:
        lines += [f"### {title}", ""]

    if not rel_paths:
        lines.append("_対象ファイルが見つかりませんでした。_")
        return "\n".join(lines)

    for rel in rel_paths:
        abs_path = (repo_root / rel).resolve()
        if not abs_path.exists() or not abs_path.is_file():
            lines.append(f"<!-- Missing: {rel} -->")
            continue

        content = read_text_safely(abs_path)
        if len(rel_paths) > 1:
            lines += [f"#### `{rel}`", ""]

        if fence:
            lines += [f"```{fence}", content.rstrip("\n"), "```", ""]
        else:
            # コードフェンスなしでそのまま挿入（Markdown衝突回避のため末尾に空行）
            lines += [content.rstrip("\n"), ""]

    # 末尾の空行調整
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)

# =============================
# Front-matter 更新
# =============================

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

def update_front_matter_last_updated(md_text: str, iso_now: str) -> str:
    m = FRONT_MATTER_RE.match(md_text)
    if not m:
        return md_text
    fm = m.group(1)
    if re.search(r"(?m)^\s*last_updated\s*:", fm):
        fm = re.sub(r"(?m)^(\s*last_updated\s*:\s*).*$", rf"\1{iso_now}", fm)
    else:
        fm = fm.rstrip() + f"\nlast_updated: {iso_now}\n"
    return md_text[:m.start(1)] + fm + md_text[m.end(1):]

# =============================
# ドキュメント更新本体
# =============================

@dataclasses.dataclass
class UpdateResult:
    path: Path
    changed: bool
    message: str

def update_markdown_file(
    md_path: Path,
    repo_root: Path,
    dry_run: bool,
    create_backup: bool,
) -> UpdateResult:
    text = md_path.read_text(encoding="utf-8")
    blocks = find_autodoc_blocks(text)
    if not blocks:
        return UpdateResult(md_path, False, "No AUTODOC blocks.")

    new_text = text
    offset = 0
    total_changes = 0

    for blk in blocks:
        attrs = blk.attrs
        mode = (attrs.get("mode") or "git_log").strip().lower()
        glob_text = attrs.get("path_globs")
        if not glob_text:
            # 指定なしはスキップ（本文はそのまま）
            continue

        title = attrs.get("title")
        paths = resolve_globs(glob_text, repo_root)

        if mode == "file_content":
            fence = attrs.get("fence")  # e.g. mermaid, python, json, md
            section_md = render_file_contents_section(repo_root, title=title, rel_paths=paths, fence=fence)
        else:
            # git_log (default)
            limit = int(attrs.get("limit", "50"))
            since = attrs.get("since")
            author = attrs.get("author")
            include_files = parse_bool(attrs.get("include_files"), True)
            entries = git_log_for_paths(repo_root, paths, limit=limit, since=since, author=author)
            section_md = render_git_section(title=title, entries=entries, include_files=include_files)

        # 置換反映（BEGIN〜ENDの本文のみ）
        body_start = blk.body_span[0] + offset
        body_end   = blk.body_span[1] + offset
        replacement = "\n" + section_md + "\n"
        new_text = new_text[:body_start] + replacement + new_text[body_end:]
        offset += len(replacement) - (body_end - body_start)
        total_changes += 1

    # front-matter の最終更新時刻
    updated_text = update_front_matter_last_updated(new_text, now_iso_jst())

    if updated_text != text and total_changes > 0:
        if dry_run:
            return UpdateResult(md_path, False, f"Would update ({total_changes} block(s)).")
        else:
            if create_backup:
                md_path.with_suffix(md_path.suffix + ".bak").write_text(text, encoding="utf-8")
            md_path.write_text(updated_text, encoding="utf-8")
            return UpdateResult(md_path, True, f"Updated ({total_changes} block(s)).")
    else:
        return UpdateResult(md_path, False, "No changes applied.")

# =============================
# CLI
# =============================

def collect_markdown_files(docs_root: Path) -> List[Path]:
    return [Path(p) for p in glob.glob(str(docs_root / "**" / "*.md"), recursive=True)]

def main():
    parser = argparse.ArgumentParser(description="Auto-update Markdown docs based on AUTODOC markers.")
    parser.add_argument("--docs-root", type=Path, default=Path("docs"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--dry-run", type=lambda x: str(x).lower() in ("1","true","yes","y"), default=False)
    parser.add_argument("--backup",  type=lambda x: str(x).lower() in ("1","true","yes","y"), default=True)
    args = parser.parse_args()

    docs_root = args.docs_root.resolve()
    repo_root = args.repo_root.resolve()

    if not docs_root.exists():
        print(f"❌ docs-root not found: {docs_root}")
        sys.exit(2)
    if not is_git_repo(repo_root):
        print(f"❌ Not a git repository: {repo_root}")
        sys.exit(2)

    md_files = collect_markdown_files(docs_root)
    print(f"# Auto Doc Update Log\n- docs_root: `{docs_root}`\n- repo_root: `{repo_root}`\n- generated_at: {now_iso_jst()}\n- dry_run: {args.dry_run}\n")

    changed = 0
    for md in sorted(md_files):
        try:
            res = update_markdown_file(md, repo_root, dry_run=args.dry_run, create_backup=args.backup)
            icon = "✅" if res.changed else "—"
            print(f"## {md.relative_to(docs_root)}\n- {icon} {res.message}\n")
            if res.changed:
                changed += 1
        except Exception as e:
            print(f"## {md.relative_to(docs_root)}\n- ❌ Error: {e}\n")

    print(f"Summary: changed={changed}, scanned={len(md_files)}")
    if args.dry_run:
        print("Note: dry-run mode; no files were written.")

if __name__ == "__main__":
    main()
