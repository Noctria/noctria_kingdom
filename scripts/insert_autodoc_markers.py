#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
insert_autodoc_markers.py — Noctria AutoDoc Marker Inserter v2.0

機能（後方互換）:
  1) 従来の「マーカーだけ挿入」(insert rules)
     - YAML/JSON の `rules:` で、指定位置に AUTODOC (BEGIN/END) を追加
  2) 本文も AUTODOC 化（wrap rules）
     - `wrap_rules:` で、見出しにマッチするセクション本文を partial ファイルへ退避
       し、その場所を AUTODOC (mode=file_content) ブロックに置換

特長:
  - dry-run / .bak バックアップ対応
  - 既存の `rules:` はそのまま使える（後方互換）
  - `wrap_rules:` を足すだけで本文も自動更新の対象に

設定ファイル（YAML/JSON）例:
  # 1) 従来のマーカー挿入
  rules:
    - match: "observability/Observability.md"
      position: "after_h1"                  # after_h1 | end | regex:<pattern>
      only_if_missing: true
      blocks:
        - mode: "file_content"
          path_globs: "docs/architecture/diagrams/act_layer.mmd"
          fence: "mermaid"
          title: "Act Layer Mermaid図（最新）"
        - mode: "git_log"
          path_globs: "src/plan_data/*.py;src/plan_data/**/*.py"
          limit: 20
          since: "2025-08-01"
          author: "Noctoria"
          title: "PlanData 変更履歴（最近20）"

  # 2) 本文をセクション単位で wrap（対象化）
  wrap_rules:
    - file: "apis/Do-Layer-Contract.md"               # docs からの相対パス
      partials_root: "docs/_partials/apis/Do-Layer-Contract"  # repo-root 相対
      keep_heading: true
      sections:
        - heading_regex: "^##\\s*1\\)\\s*スコープ\\s*&\\s*原則"
          slug: "01_scope_principles"
          title: "スコープ & 原則（最新）"           # AUTODOC セクション見出し（任意）
          fence: ""                                   # Markdown素のままなら空
        - heading_regex: "^##\\s*2\\)\\s*フロー（概観）"
          slug: "02_flow_overview"
          title: "フロー（概観）"
          fence: ""                                   # 既に本文側に ```mermaid``` があるなら空のまま

使い方:
  python3 scripts/insert_autodoc_markers.py \
    --docs-root docs \
    --config docs/autodoc_rules.yaml \
    --dry-run True

  本番:
  python3 scripts/insert_autodoc_markers.py \
    --docs-root docs \
    --config docs/autodoc_rules.yaml \
    --dry-run False
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # pyyaml が無ければ JSON でも可
    HAS_YAML = True
except Exception:
    HAS_YAML = False

# =============================
# 共通
# =============================

BEGIN_TMPL_INSERT = "<!-- AUTODOC:BEGIN {attrs} -->"
END_TMPL          = "<!-- AUTODOC:END -->"

BEGIN_TMPL_WRAP   = "<!-- AUTODOC:BEGIN mode=file_content path_globs={path} title={title}{fence_attr} -->"

AUTODOC_BEGIN_RE  = re.compile(r"<!--\s*AUTODOC:BEGIN\b", re.IGNORECASE)
H1_RE             = re.compile(r"(?m)^\s*#\s+.*?$")
H2_RE             = re.compile(r"(?m)^##\s+.*$")  # 同レベル見出し

def _quote_if_needed(val: Optional[str]) -> str:
    if val is None:
        return '""'
    if re.search(r'\s|;|=|"|\'', val):
        return '"' + val.replace('"', '\\"') + '"'
    return val

def _write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")

# =============================
# Insert（従来機能）
# =============================

@dataclass
class BlockSpec:
    mode: str                      # "git_log" | "file_content"
    path_globs: str
    title: Optional[str] = None
    fence: Optional[str] = None    # file_content 時のコードフェンス
    limit: Optional[int] = None    # git_log
    since: Optional[str] = None    # git_log
    author: Optional[str] = None   # git_log

@dataclass
class InsertRule:
    match: str                     # docs からの相対 or glob
    position: str                  # "after_h1" | "end" | "regex:<pattern>"
    only_if_missing: bool
    blocks: List[BlockSpec]

def _build_attrs_for_insert(block: BlockSpec) -> str:
    attrs: List[str] = [f"mode={block.mode}", f"path_globs={_quote_if_needed(block.path_globs)}"]
    if block.title:
        attrs.append(f"title={_quote_if_needed(block.title)}")
    if block.fence:
        attrs.append(f"fence={_quote_if_needed(block.fence)}")
    if block.limit is not None:
        attrs.append(f"limit={block.limit}")
    if block.since:
        attrs.append(f"since={_quote_if_needed(block.since)}")
    if block.author:
        attrs.append(f"author={_quote_if_needed(block.author)}")
    return " ".join(attrs)

def _build_block_text_for_insert(block: BlockSpec) -> str:
    attrs = _build_attrs_for_insert(block)
    body = "(自動置換)"
    return f"{BEGIN_TMPL_INSERT.format(attrs=attrs)}\n{body}\n{END_TMPL}\n"

def _find_insert_index(text: str, position: str) -> int:
    if position == "end":
        return len(text)
    if position == "after_h1":
        m = H1_RE.search(text)
        if not m:
            return 0
        line_end = text.find("\n", m.end())
        return len(text) if line_end == -1 else (line_end + 1)
    if position.startswith("regex:"):
        pat = position[len("regex:"):]
        try:
            rx = re.compile(pat, re.MULTILINE)
            m = rx.search(text)
            if m:
                nl = text.find("\n", m.end())
                return len(text) if nl == -1 else (nl + 1)
        except re.error:
            pass
        return len(text)
    return len(text)

def _apply_insert_rule(md_path: Path, rule: InsertRule, dry_run: bool, backup: bool) -> Tuple[bool, str]:
    text = md_path.read_text(encoding="utf-8")
    if rule.only_if_missing and AUTODOC_BEGIN_RE.search(text):
        return (False, "Skipped (already has AUTODOC block)")

    insert_at = _find_insert_index(text, rule.position)
    pieces: List[str] = []
    for b in rule.blocks:
        pieces.append(_build_block_text_for_insert(b))
        pieces.append("\n")
    insert_text = "".join(pieces).rstrip() + "\n"

    new_text = text[:insert_at] + ("\n" if (insert_at > 0 and text[insert_at-1] != "\n") else "") + insert_text + text[insert_at:]
    if new_text == text:
        return (False, "No changes")

    if dry_run:
        return (False, f"Would insert {len(rule.blocks)} block(s) at {rule.position}")
    if backup:
        md_path.with_suffix(md_path.suffix + ".bak").write_text(text, encoding="utf-8")
    _write(md_path, new_text)
    return (True, f"Inserted {len(rule.blocks)} block(s) at {rule.position}")

# =============================
# Wrap（本文を partial 化して AUTODOC に差し替え）
# =============================

@dataclass
class SectionSpec:
    heading_regex: str
    slug: str
    title: Optional[str] = None
    fence: Optional[str] = None  # ここで明示的に mermaid などを付けたい場合（通常は空推奨）

@dataclass
class WrapRule:
    file: str               # docs からの相対
    partials_root: str      # repo-root 相対
    sections: List[SectionSpec]
    keep_heading: bool = True

def _find_section_span(text: str, heading_rx: re.Pattern) -> Optional[Tuple[int,int,int,int]]:
    """
    見出し行と本文範囲:
      returns (heading_start, heading_end, body_start, body_end)
    本文: 見出し行直後 ～ 次の "## " 見出し手前（なければ末尾）
    """
    m = heading_rx.search(text)
    if not m:
        return None
    h_s, h_e = m.start(), m.end()
    nxt = H2_RE.search(text, h_e)
    body_start = h_e + 1 if h_e < len(text) and text[h_e] == "\n" else h_e
    body_end = nxt.start() if nxt else len(text)
    return (h_s, h_e, body_start, body_end)

def _apply_wrap_rule(
    docs_root: Path,
    repo_root: Path,
    rule: WrapRule,
    dry_run: bool,
    backup: bool
) -> Tuple[bool, str]:
    md_path = (docs_root / rule.file).resolve()
    if not md_path.exists():
        return (False, f"Not found: {md_path}")

    text = md_path.read_text(encoding="utf-8")
    orig = text
    total = 0
    partials_root_abs = (repo_root / rule.partials_root).resolve()
    partials_root_abs.mkdir(parents=True, exist_ok=True)

    # 一括置換で位置ズレを避けるため、後ろから処理
    matches: List[Tuple[SectionSpec, Tuple[int,int,int,int]]] = []
    for s in rule.sections:
        rx = re.compile(s.heading_regex, re.MULTILINE)
        span = _find_section_span(text, rx)
        if span:
            matches.append((s, span))

    for s, (h_s, h_e, b_s, b_e) in reversed(matches):
        body = text[b_s:b_e]

        # partial 保存パス（repo-root 相対で記録し、path_globs に使う）
        partial_rel = Path(rule.partials_root) / f"{s.slug}.md"
        partial_abs = (repo_root / partial_rel).resolve()

        if not dry_run:
            partial_abs.parent.mkdir(parents=True, exist_ok=True)
            _write(partial_abs, body)

        title_attr = _quote_if_needed(s.title) if s.title else '""'
        fence_attr = f" fence={_quote_if_needed(s.fence)}" if (s.fence is not None and s.fence != "") else ""
        block = f"{BEGIN_TMPL_WRAP.format(path=_quote_if_needed(str(partial_rel).replace('\\', '/')), title=title_attr, fence_attr=fence_attr)}\n(自動置換)\n{END_TMPL}\n"

        if rule.keep_heading:
            new_sec = text[h_s:h_e] + "\n" + block
            text = text[:h_s] + new_sec + text[b_e:]
        else:
            text = text[:h_s] + block + text[b_e:]

        total += 1

    if total == 0:
        return (False, "No sections matched")

    if dry_run:
        return (False, f"Would wrap {total} section(s)")

    if backup:
        _write(md_path.with_suffix(md_path.suffix + ".bak"), orig)
    _write(md_path, text)
    return (True, f"Wrapped {total} section(s)")

# =============================
# Config 読み込み
# =============================

def _load_config(cfg_path: Path) -> Dict[str, Any]:
    text = cfg_path.read_text(encoding="utf-8")
    if cfg_path.suffix.lower() in (".yaml", ".yml"):
        if not HAS_YAML:
            raise RuntimeError("PyYAML がありません。`pip install pyyaml` するか JSON 形式にしてください。")
        return yaml.safe_load(text)
    return json.loads(text)

def _parse_insert_rules(cfg: Dict[str, Any]) -> List[InsertRule]:
    rules_cfg = cfg.get("rules", [])
    rules: List[InsertRule] = []
    for r in rules_cfg:
        blocks: List[BlockSpec] = []
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
        rules.append(InsertRule(
            match=r["match"],
            position=r.get("position", "end"),
            only_if_missing=bool(r.get("only_if_missing", True)),
            blocks=blocks
        ))
    return rules

def _parse_wrap_rules(cfg: Dict[str, Any]) -> List[WrapRule]:
    wraps_cfg = cfg.get("wrap_rules", [])
    wraps: List[WrapRule] = []
    for w in wraps_cfg:
        sections = [SectionSpec(
            heading_regex=s["heading_regex"],
            slug=s["slug"],
            title=s.get("title"),
            fence=s.get("fence"),
        ) for s in w.get("sections", [])]
        wraps.append(WrapRule(
            file=w["file"],
            partials_root=w["partials_root"],
            sections=sections,
            keep_heading=bool(w.get("keep_heading", True)),
        ))
    return wraps

def _resolve_targets(docs_root: Path, pattern: str) -> List[Path]:
    p = docs_root / pattern
    matches = glob.glob(str(p), recursive=True)
    if not matches:
        if p.exists():
            return [p]
        return []
    return [Path(m) for m in matches]

# =============================
# main
# =============================

def main():
    ap = argparse.ArgumentParser(description="Insert AUTODOC markers and/or wrap Markdown sections into AUTODOC blocks.")
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
    insert_rules = _parse_insert_rules(cfg)
    wrap_rules   = _parse_wrap_rules(cfg)

    print("# AutoDoc Marker + Wrapper Log")
    print(f"- docs_root: `{docs_root}`")
    print(f"- repo_root: `{repo_root}`")
    print(f"- config: `{args.config}`")
    print(f"- dry_run: {args.dry_run}\n")

    changed = 0
    scanned = 0

    # 1) wrap_rules（本文対象化）— 明示的に指定されたファイルだけ
    for w in wrap_rules:
        scanned += 1
        updated, msg = _apply_wrap_rule(docs_root, repo_root, w, dry_run=args.dry_run, backup=args.backup)
        icon = "✅" if updated else "—"
        print(f"## [wrap] {w.file}\n- {icon} {msg}\n")
        if updated:
            changed += 1

    # 2) rules（従来のマーカー挿入）
    for rule in insert_rules:
        targets = _resolve_targets(docs_root, rule.match)
        if not targets:
            print(f"## [insert] {rule.match}\n- — No target files matched.\n")
            continue
        for md in sorted(targets):
            scanned += 1
            try:
                updated, msg = _apply_insert_rule(md, rule, dry_run=args.dry_run, backup=args.backup)
                icon = "✅" if updated else "—"
                print(f"## [insert] {md.relative_to(docs_root)}\n- {icon} {msg}\n")
                if updated:
                    changed += 1
            except Exception as e:
                print(f"## [insert] {md.relative_to(docs_root)}\n- ❌ Error: {e}\n")

    print(f"Summary: changed={changed}, scanned={scanned}")
    if args.dry_run:
        print("Note: dry-run mode; no files were written.")

if __name__ == "__main__":
    main()
