#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_py_import_graph.py
- 指定ディレクトリ以下の .py をASTで解析し、ファイル間の import 依存を抽出
- 出力は CSV: source_path,target_path
- 相対/絶対importをできる範囲で解決（best-effort）
"""

from __future__ import annotations
import ast
import sys
from pathlib import Path
from typing import Dict, Set, Tuple, List, Optional

EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", ".ipynb_checkpoints"}


def walk_py_files(roots: List[Path]) -> List[Path]:
    files = []
    for root in roots:
        root = root.resolve()
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            files.append(p)
    return files


def module_name_for(path: Path, roots: List[Path]) -> Optional[str]:
    # roots のいずれか配下なら module パスを推定
    try:
        for r in roots:
            r = r.resolve()
            if r in path.resolve().parents or r == path.resolve().parent or r == path.resolve():
                rel = path.resolve().relative_to(r)
                parts = list(rel.with_suffix("").parts)
                return ".".join(parts)
    except Exception:
        pass
    return None


def resolve_import(
    cur_mod: str, imp_mod: Optional[str], level: int, roots: List[Path]
) -> Optional[str]:
    """
    from .foo import bar のような相対importをモジュール名に解決。
    cur_mod: 現在ファイルの module 名（a.b.c）
    imp_mod: import 文のモジュール名（None 可）
    level : from ...x import のドット数
    """
    if level == 0:
        return imp_mod
    # 相対
    base_parts = cur_mod.split(".") if cur_mod else []
    if level <= len(base_parts):
        parent = base_parts[: len(base_parts) - level]
        if imp_mod:
            return ".".join(parent + imp_mod.split("."))
        else:
            return ".".join(parent)
    return imp_mod


def module_to_path(mod: str, roots: List[Path]) -> Optional[Path]:
    """
    モジュール名 a.b.c を ファイル a/b/c.py または a/b/c/__init__.py に解決
    """
    parts = mod.split(".")
    for r in roots:
        cand = r.joinpath(*parts).with_suffix(".py")
        if cand.exists():
            return cand
        cand2 = r.joinpath(*parts, "__init__.py")
        if cand2.exists():
            return cand2
    return None


def extract_edges(roots: List[Path]) -> Set[Tuple[str, str]]:
    files = walk_py_files(roots)
    mod_map: Dict[str, Path] = {}
    for f in files:
        m = module_name_for(f, roots)
        if m:
            mod_map[m] = f

    edges: Set[Tuple[str, str]] = set()
    for f in files:
        cur_mod = module_name_for(f, roots) or ""
        try:
            src = f.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except Exception:
            continue
        # import X, import X as Y
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    tgt = module_to_path(mod, roots)
                    if tgt:
                        edges.add((str(f.resolve()), str(tgt.resolve())))
            elif isinstance(node, ast.ImportFrom):
                imp_mod = node.module  # may be None
                mod_resolved = resolve_import(cur_mod, imp_mod, node.level or 0, roots)
                if mod_resolved:
                    tgt = module_to_path(mod_resolved, roots)
                    if tgt:
                        edges.add((str(f.resolve()), str(tgt.resolve())))
    return edges


def main():
    if len(sys.argv) < 3:
        print("Usage: scan_py_import_graph.py <out_csv> <root1> [<root2> ...]", file=sys.stderr)
        sys.exit(2)
    out = Path(sys.argv[1])
    roots = [Path(p) for p in sys.argv[2:]]
    edges = extract_edges(roots)
    out.write_text("\n".join(f"{s},{t}" for s, t in sorted(edges)), encoding="utf-8")
    print(f"[ok] wrote {out}  edges={len(edges)}")


if __name__ == "__main__":
    main()
