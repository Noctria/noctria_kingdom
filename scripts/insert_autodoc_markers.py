#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
insert_autodoc_markers.py — Noctria AutoDoc Marker Inserter v1.0

目的:
  既存の Markdown ファイル群に AUTODOC ブロック（BEGIN/END）を一括挿入する。

特徴:
  - YAML/JSON の設定で対象 md を指定し、複数ブロックを柔軟に追加
  - 既存に AUTODOC ブロックがある場合はスキップ（重複防止）
  - 挿入位置: after_h1 / end / regex:<pattern>
  - .bak バックアップ作成 & --dry-run プレビュー対応
  - UTF-8 前提

使い方（例）:
  python3 scripts/insert_autodoc_markers.py \
    --docs-root docs \
    --config docs/autodoc_rules.yaml \
    --dry-run True

本番適用:
  python3 scripts/insert_autodoc_markers.py \
    --docs-root docs \
    --config docs/autodoc_rules.yaml \
    --dry-run False

設定ファイル（YAML/JSON）仕様:
  rules:
    - match: "observability/Observability.md"        # docs からの相対パス or mdのglob
      position: "after_h1"                           # after_h1 | end | regex:^# Observability
      only_if_missing: true                          # 既存の AUTODOC ブロックがあれば挿入しない
      blocks:
        - mode: "file_content"
          path_globs: "docs/architecture/diagrams/act_layer.mmd"
          fence: "mermaid"
          title: "Act Layer Mermaid図（最新）"
        - mode: "git_log"
          path_globs: "src/plan_data/*.py;src/plan_data/**/*.py"
          limit: 20
          title: "PlanData 変更履歴（最近20）"
          since: "2025-08-01"
          author: "Noctoria"

    - match: "adrs/ADRs.md"
      position: "end"
      only_if_missing: false
      blocks:
        - mode: "git_log"
          path_globs: "docs/adrs/*.md"
          limit: 50
          title: "ADRファイルの更新履歴"

"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # pyyaml が無ければ JSON で代用可
    HAS_YAML = True
except Exception:
    HAS_YAML = False


BEGIN_TMPL = "<!-- AUTODOC:BEGIN {attrs} -->"
END_TMPL   = "<!-- AUTODOC:END -->"

AUTODOC_BEGIN_RE = re.compile(r"<!--\s*AUTODOC:BEGIN\b", re.IGNORECASE)

H1_RE = re.compile(r"(?m)^\s*#\s+.*?$")

@dataclass
class BlockSpec:
    mode: str                      # "git_log" or "file_content"
    path_globs: str
    title: Optional[str] = None
    fence: Optional[str] = None    # file_contentでコードフェンス指定
    limit: Optional[int] = None    # git_log
    since: Optional[str] = None    # git_log
    author: Optional[str] = None   # git_log

@dataclass
class Rule:
    match: str                     # 対象 md （相対パス or glob）
    position: str                  # "after_h1" | "end" | "regex:<pattern>"
    only_if_missing: bool
    blocks: List[BlockSpec]

def load_config(cfg_path: Path) -> Dict[str, Any]:
    text = cfg_path.read_text(encoding="utf-8")
    if cfg_path.suffix.lower() in (".yaml", ".yml"):
        if not HAS_YAML:
            raise RuntimeError("PyYAML がありません。`pip install pyyaml` するか JSON 形式で設定を書いてください。")
        return yaml.safe_load(text)
    else:
        return json.loads(text)

def parse_rules(cfg: Dict[str, Any]) -> List[Rule]:
    rules: List[Rule] = []
    for r in cfg.get("rules", []):
        blocks = []
        for b in r.get("blocks", []):
            blocks.append(BlockSpec(
                mode=b.get("mode", "git_log"),
                path_globs=b["path_globs"],
                title=b.get("title"),
                fence=b.get("fence"),
                limit=b.get("limit"),
                since=b.get("since"),
                author=b.get("author"),
            ))
        rules.append(Rule(
            match=r["match"],
            position=r.get("position", "end"),
            only_if_missing=bool(r.get("only_if_missing", True)),
            blocks=blocks
        ))
    return rules

def build_attrs(block: BlockSpec) -> str:
    # mode と path_globs は必須として展開
    attrs: List[str] = [f'mode={block.mode}', f'path_globs={_quote_if_needed(block.path_globs)}']
    if block.title:
        attrs.append(f'title={_quote_if_needed(block.title)}')
    if block.fence:
        attrs.append(f'fence={_quote_if_needed(block.fence)}')
    if block.limit is not None:
        attrs.append(f'limit={block.limit}')
    if block.since:
        attrs.append(f'since={_quote_if_needed(block.since)}')
    if block.author:
        attrs.append(f'author={_quote_if_needed(block.author)}')
    return " ".join(attrs)

def _quote_if_needed(val: str) -> str:
    if re.search(r"\s|;|\"|'|=", val):
        # ダブルクォートで囲む（内部の"はエスケープ）
        escaped = val.replace('"', '\\"')
        return f'"{escaped}"'
    return val

def find_insert_index(text: str, position: str) -> int:
    """
    返り値: 挿入すべきインデックス（textの0..len）
    """
    if position == "end":
        return len(text)

    if position == "after_h1":
        m = H1_RE.search(text)
        if not m:
            return 0  # H1が無ければ先頭
        # H1 行の直後（行末の次）
        line_end = text.find("\n", m.end())
        return len(text) if line_end == -1 else (line_end + 1)

    if position.startswith("regex:"):
        pat = position[len("regex:"):]
        try:
            rx = re.compile(pat, re.MULTILINE)
            m = rx.search(text)
            if m:
                # マッチ部分の直後
                insert_at = m.end()
                # 次の改行があればその直後に挿入して段落整形を崩さない
                nl = text.find("\n", insert_at)
                return len(text) if nl == -1 else (nl + 1)
        except re.error:
            pass
        # 見つからなければ末尾
        return len(text)

    # 未知指定は末尾
    return len(text)

def build_block_text(block: BlockSpec) -> str:
    attrs = build_attrs(block)
    # プレースホルダは1行入れておく（update_docs_from_index.py が置換）
    body = "(自動置換)"
    return f"{BEGIN_TMPL.format(attrs=attrs)}\n{body}\n{END_TMPL}\n"

def apply_rule_to_file(md_path: Path, rule: Rule, dry_run: bool, backup: bool) -> Tuple[bool, str]:
    text = md_path.read_text(encoding="utf-8")

    if rule.only_if_missing and AUTODOC_BEGIN_RE.search(text):
        return (False, "Skipped (already has AUTODOC block)")

    insert_at = find_insert_index(text, rule.position)
    pieces: List[str] = []
    for b in rule.blocks:
        pieces.append(build_block_text(b))
        pieces.append("\n")
    insert_text = "".join(pieces).rstrip() + "\n"

    new_text = text[:insert_at] + ("\n" if (insert_at > 0 and text[insert_at-1] != "\n") else "") + insert_text + text[insert_at:]

    if new_text == text:
        return (False, "No changes")

    if dry_run:
        return (False, f"Would insert {len(rule.blocks)} block(s) at {rule.position}")

    if backup:
        md_path.with_suffix(md_path.suffix + ".bak").write_text(text, encoding="utf-8")
    md_path.write_text(new_text, encoding="utf-8")
    return (True, f"Inserted {len(rule.blocks)} block(s) at {rule.position}")

def resolve_targets(docs_root: Path, pattern: str) -> List[Path]:
    # pattern がファイル名ならそのまま、glob なら展開
    p = docs_root / pattern
    matches = glob.glob(str(p), recursive=True)
    if not matches:
        # globにヒットしないが、単一ファイルかも
        if p.exists():
            return [p]
        return []
    return [Path(m) for m in matches]

def main():
    ap = argparse.ArgumentParser(description="Insert AUTODOC markers into existing Markdown files.")
    ap.add_argument("--docs-root", type=Path, default=Path("docs"))
    ap.add_argument("--config", type=Path, required=True, help="YAML or JSON rules file")
    ap.add_argument("--dry-run", type=lambda x: str(x).lower() in ("1","true","yes","y"), default=True)
    ap.add_argument("--backup",  type=lambda x: str(x).lower() in ("1","true","yes","y"), default=True)
    args = ap.parse_args()

    docs_root = args.docs_root.resolve()
    if not docs_root.exists():
        print(f"❌ docs-root not found: {docs_root}")
        sys.exit(2)

    cfg = load_config(args.config)
    rules = parse_rules(cfg)

    print(f"# AutoDoc Marker Insertion Log")
    print(f"- docs_root: `{docs_root}`")
    print(f"- config: `{args.config}`")
    print(f"- dry_run: {args.dry_run}\n")

    changed = 0
    scanned = 0

    for rule in rules:
        targets = resolve_targets(docs_root, rule.match)
        if not targets:
            print(f"## {rule.match}\n- — No target files matched.\n")
            continue
        for md in sorted(targets):
            scanned += 1
            try:
                updated, msg = apply_rule_to_file(md, rule, dry_run=args.dry_run, backup=args.backup)
                icon = "✅" if updated else "—"
                print(f"## {md.relative_to(docs_root)}\n- {icon} {msg}\n")
                if updated:
                    changed += 1
            except Exception as e:
                print(f"## {md.relative_to(docs_root)}\n- ❌ Error: {e}\n")

    print(f"Summary: changed={changed}, scanned={scanned}")
    if args.dry_run:
        print("Note: dry-run mode; no files were written.")

if __name__ == "__main__":
    main()
