#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_py_import_graph_fast.py
- .py をASTで解析して import 依存 (source_path,target_path) を抽出
- 速い/安全：巨大ディレクトリ除外・余計な realpath/resolve を避ける・警告を抑制
- 使い方:
    python tools/scan_py_import_graph_fast.py OUT_CSV ROOT1 [ROOT2 ...] [--exclude DIR ...]
"""

from __future__ import annotations
import ast
import sys
import os
import warnings
from pathlib import Path
from typing import Dict, Set, Tuple, List, Optional

# うるさい SyntaxWarning を黙らせる（re の \w など）
warnings.filterwarnings("ignore", category=SyntaxWarning)

# デフォルト除外
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "venv_codex",
    "autogen_venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".cache",
    "node_modules",
    "dist",
    "build",
    "data",
    "viz",
    "htmlcov",
    "site-packages",
}

EXCLUDE_DIRS: Set[str] = set(DEFAULT_EXCLUDE_DIRS)


def walk_py_files(roots: List[Path]) -> List[Path]:
    files: List[Path] = []
    for root in roots:
        root = root.resolve()
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # 除外ディレクトリを prune
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                p = Path(dirpath) / fn
                files.append(p)
    return files


def module_name_for(path: Path, roots: List[Path]) -> Optional[str]:
    """roots のどれかに対する相対パスからモジュール名を推定"""
    p = path.absolute()
    for r in roots:
        r_abs = r.absolute()
        try:
            rel = p.relative_to(r_abs)
        except Exception:
            continue
        parts = list(rel.with_suffix("").parts)
        if not parts:
            continue
        return ".".join(parts)
    return None


def module_to_path(mod: str, roots: List[Path]) -> Optional[Path]:
    """a.b.c -> a/b/c.py または a/b/c/__init__.py"""
    parts = mod.split(".")
    for r in roots:
        base = r / Path(*parts)
        cand = base.with_suffix(".py")
        if cand.exists():
            return cand
        initp = base / "__init__.py"
        if initp.exists():
            return initp
    return None


def resolve_relative(cur_mod: str, imp_mod: Optional[str], level: int) -> Optional[str]:
    """from ..x import y の相対 import をモジュール名に"""
    if level == 0:
        return imp_mod
    base = cur_mod.split(".") if cur_mod else []
    if level <= len(base):
        parent = base[: len(base) - level]
        if imp_mod:
            return ".".join(parent + imp_mod.split("."))
        else:
            return ".".join(parent) if parent else None
    return imp_mod


def extract_edges(roots: List[Path]) -> Set[Tuple[str, str]]:
    roots = [r.absolute() for r in roots]
    files = walk_py_files(roots)

    # まず自分たちのモジュール表（best-effort）
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
            tree = ast.parse(src, filename=str(f))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    tgt = mod_map.get(mod) or module_to_path(mod, roots)
                    if tgt:
                        edges.add((str(f), str(tgt)))
            elif isinstance(node, ast.ImportFrom):
                imp_mod = node.module
                mod_resolved = resolve_relative(cur_mod, imp_mod, node.level or 0)
                if not mod_resolved:
                    continue
                tgt = mod_map.get(mod_resolved) or module_to_path(mod_resolved, roots)
                if tgt:
                    edges.add((str(f), str(tgt)))
    return edges


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: scan_py_import_graph_fast.py <out_csv> <root1> [<root2> ...] [--exclude DIR ...]",
            file=sys.stderr,
        )
        sys.exit(2)

    out = Path(sys.argv[1])
    args = sys.argv[2:]

    roots: List[Path] = []
    extra_excludes: List[str] = []

    i = 0
    while i < len(args):
        if args[i] == "--exclude":
            if i + 1 < len(args):
                extra_excludes.append(args[i + 1])
                i += 2
            else:
                print("Error: --exclude requires DIR", file=sys.stderr)
                sys.exit(2)
        else:
            roots.append(Path(args[i]))
            i += 1

    # 除外更新
    global EXCLUDE_DIRS
    EXCLUDE_DIRS = set(DEFAULT_EXCLUDE_DIRS) | set(extra_excludes)

    edges = extract_edges(roots)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(f"{s},{t}" for s, t in sorted(edges)), encoding="utf-8")
    print(f"[ok] wrote {out}  edges={len(edges)}  excludes={len(EXCLUDE_DIRS)}")


if __name__ == "__main__":
    main()
