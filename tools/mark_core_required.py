#!/usr/bin/env python3
# coding: utf-8
"""
mark_core_required.py v1.1
- keep_list の "ノードID or 実ファイルパス" を解決して
  各ファイルの先頭に '# [NOCTRIA_CORE_REQUIRED]' を一括挿入。
- 既に入っていればスキップ。
- 追加: ___init___py ノードIDを xxx/__init__.py に自動解決。
"""
from __future__ import annotations
import argparse, os, re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

MARK = "# [NOCTRIA_CORE_REQUIRED]"
DEFAULT_KEEP = "viz/keep_list.txt"
EXCLUDE_DIRS = {
    ".git",".hg",".svn",".venv","venv","venv_codex","autogen_venv",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".cache",
    "node_modules","dist","build","viz","htmlcov","site-packages","data",
}

def norm_id_from_relpath(rel: Path) -> str:
    s = rel.as_posix().lower()
    if s.endswith(".py"):
        s = s[:-3] + "_py"
    t = re.sub(r"[^0-9a-z]+", "_", s).strip("_")
    t = re.sub(r"_+", "_", t)
    return t

def build_nodeid_index(project_root: Path) -> Dict[str, Path]:
    idx: Dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(project_root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if not fn.endswith(".py"): continue
            p = Path(dirpath) / fn
            rel = p.relative_to(project_root)
            nodeid = norm_id_from_relpath(rel)
            if nodeid not in idx or len(str(rel)) < len(str(idx[nodeid].relative_to(project_root))):
                idx[nodeid] = p
    return idx

def parse_keep_lines(keep_file: Path) -> List[str]:
    lines: List[str] = []
    for raw in keep_file.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"): continue
        lines.append(s)
    return lines

def _try_resolve_init_nodeid(key: str, project_root: Path) -> Path | None:
    """
    'src_scripts___init___py' → project_root/'src/scripts/__init__.py' を試す。
    """
    if not key.endswith("___init___py"):
        return None
    # 末尾 ___init___py を __init__.py に変換し、残りをディレクトリに
    prefix = key[: -len("___init___py")]
    # 下線をパス区切りに戻す（粗いが実運用では十分）
    parts = [p for p in prefix.split("_") if p]
    candidate = project_root.joinpath(*parts) / "__init__.py"
    return candidate if candidate.exists() else None

def resolve_targets(items: Iterable[str], project_root: Path, nodeidx: Dict[str, Path]) -> Tuple[List[Path], List[str]]:
    found: List[Path] = []
    missing: List[str] = []
    for it in items:
        p = (project_root / it).resolve() if not Path(it).is_absolute() else Path(it)
        if p.exists() and p.suffix == ".py":
            found.append(p); continue
        key = it.strip().lower()
        if key.endswith(".py"):
            key = key[:-3] + "_py"
        # 1) 既知のインデックス
        if key in nodeidx:
            found.append(nodeidx[key]); continue
        # 2) ___init___py ヘルパ
        cand = _try_resolve_init_nodeid(key, project_root)
        if cand:
            found.append(cand); continue
        missing.append(it)
    return found, missing

def file_already_marked(p: Path) -> bool:
    try:
        head = p.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
    except Exception:
        return False
    return bool(head and head[0].strip() == MARK)

def insert_mark(p: Path, dry_run: bool = False) -> str:
    if file_already_marked(p): return f"[ok] already marked: {p}"
    if dry_run: return f"[dry] would mark: {p}"
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        p.write_text("\n".join([MARK] + txt) + "\n", encoding="utf-8")
        return f"[ok] marked: {p}"
    except Exception as e:
        return f"[err] write failed: {p} ({e})"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", default=DEFAULT_KEEP)
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    project_root = Path(args.project_root).resolve()
    keep_file = (project_root / args.keep) if not Path(args.keep).is_absolute() else Path(args.keep)
    if not keep_file.exists():
        print(f"[fatal] keep_list not found: {keep_file}"); raise SystemExit(2)

    nodeidx = build_nodeid_index(project_root)
    items = parse_keep_lines(keep_file)
    paths, missing = resolve_targets(items, project_root, nodeidx)

    count_ok = 0
    for p in paths:
        msg = insert_mark(p, dry_run=args.dry_run)
        print(msg)
        if msg.startswith("[ok]"): count_ok += 1

    if missing:
        print("\n[warn] unresolved items:")
        for it in missing: print("  -", it)
    print(f"\n[done] total targets={len(paths)}, marked_or_already={count_ok}, unresolved={len(missing)}")

if __name__ == "__main__":
    main()
