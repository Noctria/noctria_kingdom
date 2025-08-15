#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
insert_autodoc_markers.py — Full-Wrap Only (Noctria AutoDoc) v3.0

目的:
  docs 配下の Markdown を「本文全文」AUTODOC 化する。
  - 本文を repo 直下の partials へ退避（デフォルト: docs/_partials_full/<元相対パス>.md）
  - 元 md は (Front Matter を残しつつ) AUTODOC (mode=file_content) ブロックのみへ置換
  - 以降は update_docs_from_index.py 実行で md 本文が partial の内容で自動更新される

仕様:
  - YAML Front Matter (--- ... ---) は保持して、その後ろのみラップ
  - すでに AUTODOC が含まれる md はスキップ（--force で上書き可）
  - .bak バックアップ、dry-run 対応
  - include/exclude グロブで対象選択可能

使い方:
  # プレビュー
  python3 scripts/insert_autodoc_markers.py --docs-root docs --dry-run True

  # 本番（全 md を全文囲い）
  python3 scripts/insert_autodoc_markers.py --docs-root docs --dry-run False

  # 一部だけ / 除外あり
  python3 scripts/insert_autodoc_markers.py \
    --docs-root docs \
    --include "governance/**/*.md" --exclude "README.md" \
    --dry-run False

引数:
  --docs-root            : 対象ルート (既定: docs)
  --partials-root        : partial の保存ルート (repo 相対) 既定: docs/_partials_full
  --include              : 追加の対象グロブ (複数可)
  --exclude              : 除外グロブ (複数可)
  --keep-front-matter    : Front Matter を保持 (既定 True)
  --force                : 既存 AUTODOC があっても再ラップ (既定 False)
  --dry-run              : 変更せずに出力 (既定 True)
  --backup               : .bak を作る (既定 True)
"""

from __future__ import annotations

import argparse
import glob
import os
import re
from pathlib import Path
from typing import List, Tuple

BEGIN_TMPL = "<!-- AUTODOC:BEGIN mode=file_content path_globs={path} -->"
END_TMPL   = "<!-- AUTODOC:END -->"

AUTODOC_BEGIN_RE = re.compile(r"<!--\s*AUTODOC:BEGIN\b", re.IGNORECASE)
FRONT_MATTER_RE  = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

def find_front_matter_span(text: str) -> Tuple[int,int] | None:
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return None
    return (0, m.end())

def ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def should_exclude(path: Path, exclude_globs: List[str], docs_root: Path) -> bool:
    rel = path.relative_to(docs_root).as_posix()
    for g in exclude_globs:
        if Path(docs_root / g).match(str(docs_root / rel)) or glob.fnmatch.fnmatch(rel, g):
            return True
    return False

def matches_includes(path: Path, include_globs: List[str], docs_root: Path) -> bool:
    if not include_globs:
        return True
    rel = path.relative_to(docs_root).as_posix()
    for g in include_globs:
        if Path(docs_root / g).match(str(docs_root / rel)) or glob.fnmatch.fnmatch(rel, g):
            return True
    return False

def process_file(
    md_path: Path,
    docs_root: Path,
    repo_root: Path,
    partials_root: Path,
    keep_front_matter: bool,
    dry_run: bool,
    backup: bool,
    force: bool,
) -> Tuple[bool,str]:
    text = md_path.read_text(encoding="utf-8")

    if AUTODOC_BEGIN_RE.search(text) and not force:
        return (False, "Skipped (already has AUTODOC)")

    # front matter 切り分け
    fm_span = find_front_matter_span(text) if keep_front_matter else None
    if fm_span:
        fm = text[fm_span[0]:fm_span[1]]
        body = text[fm_span[1]:]
    else:
        fm = ""
        body = text

    # partial の保存先（repo 相対: docs/_partials_full/<相対パス>.md）
    rel_md = md_path.relative_to(repo_root)  # 例: docs/governance/Vision-Governance.md
    partial_path = (partials_root / rel_md).with_suffix(".md")
    ensure_dir(partial_path)
    if not dry_run:
        partial_path.write_text(body, encoding="utf-8")

    # AUTODOC ブロックへ置換（fm は残す）
    rel_for_attr = partial_path.as_posix()
    block = f"{BEGIN_TMPL.format(path=quote_attr(rel_for_attr))}\n(自動置換)\n{END_TMPL}\n"
    new_text = (fm if fm else "") + block

    if new_text == text:
        return (False, "No changes")

    if dry_run:
        # 先頭 300 文字だけプレビュー
        preview = new_text[:300].rstrip().replace("\n", "\\n")
        return (False, f"Would wrap -> {rel_for_attr} | preview: {preview}...")
    else:
        if backup:
            md_path.with_suffix(md_path.suffix + ".bak").write_text(text, encoding="utf-8")
        md_path.write_text(new_text, encoding="utf-8")
        return (True, f"Wrapped -> {rel_for_attr}")

def quote_attr(val: str) -> str:
    if re.search(r'\s|;|=|"|\'', val):
        return '"' + val.replace('"','\\"') + '"'
    return val

def collect_targets(docs_root: Path, include_globs: List[str]) -> List[Path]:
    # 既定は docs_root 配下の *.md 全部
    paths = [p for p in docs_root.rglob("*.md") if p.is_file()]
    if not include_globs:
        return sorted(paths)
    # include を明示した場合は、その union
    picked = set()
    for g in include_globs:
        for m in glob.glob(str(docs_root / g), recursive=True):
            pm = Path(m)
            if pm.is_file() and pm.suffix.lower() == ".md":
                picked.add(pm.resolve())
    return sorted(picked)

def main():
    ap = argparse.ArgumentParser(description="Full-wrap Markdown files into AUTODOC (file_content) blocks.")
    ap.add_argument("--docs-root", type=Path, default=Path("docs"))
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--partials-root", type=Path, default=Path("docs/_partials_full"),
                    help="Where to write partials (repo-root relative).")
    ap.add_argument("--include", action="append", default=[], help="Include glob(s) under docs-root (e.g. 'governance/**/*.md').")
    ap.add_argument("--exclude", action="append", default=[], help="Exclude glob(s) under docs-root.")
    ap.add_argument("--keep-front-matter", type=lambda x: str(x).lower() in ("1","true","yes","y","on"), default=True)
    ap.add_argument("--force", type=lambda x: str(x).lower() in ("1","true","yes","y","on"), default=False,
                    help="Wrap even if AUTODOC already exists.")
    ap.add_argument("--dry-run", type=lambda x: str(x).lower() in ("1","true","yes","y","on"), default=True)
    ap.add_argument("--backup", type=lambda x: str(x).lower() in ("1","true","yes","y","on"), default=True)
    args = ap.parse_args()

    docs_root = args.docs_root.resolve()
    repo_root = args.repo_root.resolve()
    partials_root = (repo_root / args.partials_root).resolve()

    if not docs_root.exists():
        print(f"❌ docs-root not found: {docs_root}")
        raise SystemExit(2)

    changed = 0
    scanned = 0

    all_targets = collect_targets(docs_root, args.include)
    for md in all_targets:
        rel = md.relative_to(docs_root).as_posix()
        if should_exclude(md, args.exclude, docs_root):
            print(f"## {rel}\n- — Excluded\n")
            continue
        scanned += 1
        try:
            updated, msg = process_file(
                md_path=md,
                docs_root=docs_root,
                repo_root=repo_root,
                partials_root=partials_root,
                keep_front_matter=args.keep_front_matter,
                dry_run=args.dry_run,
                backup=args.backup,
                force=args.force,
            )
            icon = "✅" if updated else "—"
            print(f"## {rel}\n- {icon} {msg}\n")
            if updated:
                changed += 1
        except Exception as e:
            print(f"## {rel}\n- ❌ Error: {e}\n")

    print(f"Summary: changed={changed}, scanned={scanned}")
    if args.dry_run:
        print("Note: dry-run mode; no files were written.")

if __name__ == "__main__":
    main()
