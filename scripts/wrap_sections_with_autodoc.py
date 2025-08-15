#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wrap_sections_with_autodoc.py — wrap existing Markdown sections with AUTODOC blocks
目的:
  既存の Markdown の指定セクション本文を「部分ファイル（partials）」に切り出し、
  その位置に AUTODOC (mode=file_content) ブロックを挿入する。

使い方:
  python3 scripts/wrap_sections_with_autodoc.py \
    --docs-root docs \
    --config docs/wrap_rules.yaml \
    --dry-run True

設定ファイル仕様 (YAML/JSON):
  rules:
    - file: "apis/Do-Layer-Contract.md"         # docs からの相対パス
      partials_root: "docs/_partials/apis/Do-Layer-Contract"  # 部分ファイル保存先（リポジトリ相対）
      sections:
        - heading_regex: "^##\\s*1\\)\\s*スコープ\\s*&\\s*原則"   # セクションの見出しにマッチ（行頭^対応）
          slug: "01_scope_principles"                           # 部分ファイル名の基（.md が付く）
          title: "スコープ & 原則（最新）"                        # AUTODOC セクション見出しに表示（任意）
          fence: ""                                             # Markdown を素で埋めたいので空推奨
        - heading_regex: "^##\\s*2\\)\\s*フロー（概観）"
          slug: "02_flow_overview"
          title: "フロー（概観）"
          fence: ""                                             # 既に別の Mermaid ブロックがあるなら "" のまま
      keep_heading: true   # セクション見出し行は残し、本文だけを置換

注意:
  - 見出しレベルは "##" 固定想定（必要なら増やせます）
  - セクション本文の範囲は「見出し行の次行 ～ 次の同レベル見出し直前」。
  - すでに AUTODOC が本文内にある場合は、そのまま上書き置換されます（partials に現状を書き出します）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
    HAS_YAML = True
except Exception:
    HAS_YAML = False


BEGIN_TMPL = "<!-- AUTODOC:BEGIN mode=file_content path_globs={path} title={title} -->"
END_TMPL   = "<!-- AUTODOC:END -->"

H2_RE = re.compile(r"(?m)^##\s+.*$")  # 同レベル見出しの検出用

@dataclass
class SectionRule:
    heading_regex: str
    slug: str
    title: Optional[str] = None
    fence: Optional[str] = None

@dataclass
class FileRule:
    file: str
    partials_root: str
    sections: List[SectionRule]
    keep_heading: bool = True

def _load_config(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yml", ".yaml"):
        if not HAS_YAML:
            raise RuntimeError("PyYAML が必要です。`pip install pyyaml` を実行するか JSON に変換してください。")
        return yaml.safe_load(text)
    return json.loads(text)

def _quote_if_needed(val: str) -> str:
    if val is None:
        return '""'
    if re.search(r'\s|;|=|"|\'', val):
        return '"' + val.replace('"', '\\"') + '"'
    return val

def _find_section_span(text: str, heading_rx: re.Pattern) -> Optional[Tuple[int,int,int,int]]:
    """
    見出し行の span と本文の span を返す:
      returns (heading_start, heading_end, body_start, body_end)
    body_end は次の H2 見出し手前（なければ末尾）
    """
    m = heading_rx.search(text)
    if not m:
        return None
    heading_start, heading_end = m.start(), m.end()

    # 次の H2 を探す（自身の終端から）
    next_h2 = H2_RE.search(text, heading_end)
    body_start = heading_end + 1 if heading_end < len(text) and text[heading_end] == "\n" else heading_end
    body_end = next_h2.start() if next_h2 else len(text)
    return (heading_start, heading_end, body_start, body_end)

def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def _write_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")

def _wrap_one_file(docs_root: Path, repo_root: Path, rule: FileRule, dry_run: bool, backup: bool) -> Tuple[bool,str]:
    md_path = (docs_root / rule.file).resolve()
    if not md_path.exists():
        return (False, f"Not found: {md_path}")

    text = md_path.read_text(encoding="utf-8")
    orig_text = text
    total_changes = 0

    partials_root_abs = (repo_root / rule.partials_root).resolve()
    _ensure_dir(partials_root_abs)

    # セクション順に処理（前から置換すると index がずれるので、後ろの方から処理）
    # → 一旦マッチ位置を集めてから後方へ向けて置換
    matches: List[Tuple[SectionRule, Tuple[int,int,int,int]]] = []
    for s in rule.sections:
        heading_rx = re.compile(s.heading_regex, re.MULTILINE)
        span = _find_section_span(text, heading_rx)
        if span:
            matches.append((s, span))

    # 後ろから
    for s, (h_s, h_e, b_s, b_e) in reversed(matches):
        body = text[b_s:b_e]

        # 部分ファイルパス作成
        partial_path_rel = Path(rule.partials_root) / f"{s.slug}.md"
        partial_path_abs = (repo_root / partial_path_rel).resolve()

        # 既存本文を部分ファイルへ書き出し
        if not dry_run:
            _ensure_dir(partial_path_abs.parent)
            _write_file(partial_path_abs, body)

        # AUTODOC ブロック生成
        title_attr = _quote_if_needed(s.title) if s.title else '""'
        path_attr = _quote_if_needed(str(partial_path_rel).replace("\\", "/"))
        block = f"{BEGIN_TMPL.format(path=path_attr, title=title_attr)}\n(自動置換)\n{END_TMPL}\n"

        # 置換（見出しを残す or 含める）
        if rule.keep_heading:
            new_section = text[h_s:h_e] + "\n" + block
            text = text[:h_s] + new_section + text[b_e:]
        else:
            # 見出し含めてブロックだけに差し替え
            text = text[:h_s] + block + text[b_e:]

        total_changes += 1

    if total_changes == 0:
        return (False, "No sections matched")

    if dry_run:
        return (False, f"Would wrap {total_changes} section(s)")

    # バックアップ
    if backup:
        bak = md_path.with_suffix(md_path.suffix + ".bak")
        _write_file(bak, orig_text)

    _write_file(md_path, text)
    return (True, f"Wrapped {total_changes} section(s)")

def main():
    ap = argparse.ArgumentParser(description="Wrap Markdown sections with AUTODOC blocks and extract bodies to partial files.")
    ap.add_argument("--docs-root", type=Path, default=Path("docs"))
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--dry-run", type=lambda x: str(x).lower() in ("1","true","yes","y"), default=True)
    ap.add_argument("--backup",  type=lambda x: str(x).lower() in ("1","true","yes","y"), default=True)
    args = ap.parse_args()

    docs_root = args.docs_root.resolve()
    repo_root = args.repo_root.resolve()

    if not docs_root.exists():
        print(f"❌ docs-root not found: {docs_root}")
        sys.exit(2)

    cfg = _load_config(args.config)
    rules_cfg = cfg.get("rules", [])
    if not rules_cfg:
        print("❌ No rules in config")
        sys.exit(2)

    changed = 0
    scanned = 0

    for r in rules_cfg:
        sections = [SectionRule(**s) for s in r.get("sections", [])]
        file_rule = FileRule(
            file=r["file"],
            partials_root=r["partials_root"],
            sections=sections,
            keep_heading=bool(r.get("keep_heading", True)),
        )
        updated, msg = _wrap_one_file(docs_root, repo_root, file_rule, dry_run=args.dry_run, backup=args.backup)
        scanned += 1
        icon = "✅" if updated else "—"
        print(f"## {file_rule.file}\n- {icon} {msg}\n")
        if updated:
            changed += 1

    print(f"Summary: changed={changed}, scanned={scanned}")
    if args.dry_run:
        print("Note: dry-run mode; no files were written.")

if __name__ == "__main__":
    main()
