#!/usr/bin/env python3
# coding: utf-8
"""
seeds_from_marker.py
- リポジトリ内の '# [NOCTRIA_CORE_REQUIRED]' で始まる .py を列挙
- node id と実ファイルパスを出力する（重複は自動スキップ）
- 既存の seeds/keep_list を上書きする運用想定（--append で追記も可）

使い方:
  python3 tools/seeds_from_marker.py \
    --project-root /mnt/d/noctria_kingdom \
    --graph-json viz/graph_overview_with_imports.json \
    --seeds-out viz/seeds.txt \
    --keep-out viz/keep_list.txt
"""

from __future__ import annotations
import argparse
import json
import os
import re
from pathlib import Path
from typing import List, Set

MARK = "# [NOCTRIA_CORE_REQUIRED]"
EXCLUDE_DIRS = {
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
    "viz",
    "htmlcov",
    "site-packages",
    "data",
}


def norm_id_from_relpath(rel: Path) -> str:
    s = rel.as_posix().lower()
    if s.endswith(".py"):
        s = s[:-3] + "_py"
    t = re.sub(r"[^0-9a-z]+", "_", s).strip("_")
    t = re.sub(r"_+", "_", t)
    return t


def collect_marked_files(project_root: Path) -> List[Path]:
    found: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(project_root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = Path(dirpath) / fn
            try:
                head = p.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
            except Exception:
                continue
            if head and head[0].strip() == MARK:
                found.append(p)
    return found


def graph_ids(graph_json: Path) -> Set[str]:
    ids: Set[str] = set()
    if not graph_json or not graph_json.exists():
        return ids
    try:
        obj = json.loads(graph_json.read_text(encoding="utf-8"))
        els = obj.get("elements") or {}
        for n in els.get("nodes") or []:
            d = (n or {}).get("data") or {}
            nid = d.get("id")
            if isinstance(nid, str):
                ids.add(nid)
    except Exception:
        pass
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--graph-json", default="")
    ap.add_argument("--seeds-out", default="viz/seeds.txt")
    ap.add_argument("--keep-out", default="viz/keep_list.txt")
    ap.add_argument("--append", action="store_true", help="既存ファイルに追記（既定は上書き）")
    args = ap.parse_args()

    project_root = Path(args.project_root).resolve()
    seeds_out = (
        (project_root / args.seeds_out)
        if not Path(args.seeds_out).is_absolute()
        else Path(args.seeds_out)
    )
    keep_out = (
        (project_root / args.keep_out)
        if not Path(args.keep_out).is_absolute()
        else Path(args.keep_out)
    )
    graph_path = Path(args.graph_json) if args.graph_json else None
    if graph_path and not graph_path.is_absolute():
        graph_path = project_root / graph_path

    marked = collect_marked_files(project_root)
    if not marked:
        print("[warn] no marked files found.")
    # node id / path をユニーク化
    node_ids: List[str] = []
    file_paths: List[str] = []
    seen_ids: Set[str] = set()
    seen_paths: Set[str] = set()

    graph_id_set: Set[str] = graph_ids(graph_path) if graph_path and graph_path.exists() else set()

    for p in marked:
        rel = p.relative_to(project_root)
        nid = norm_id_from_relpath(rel)
        # graph に存在しない Node ID はそのままでも OK（後工程が解決可能）
        if nid not in seen_ids:
            node_ids.append(nid)
            seen_ids.add(nid)
        sp = rel.as_posix()
        if sp not in seen_paths:
            file_paths.append(sp)
            seen_paths.add(sp)

    # 書き込み（上書き or 追記）
    seeds_out.parent.mkdir(parents=True, exist_ok=True)
    keep_out.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if args.append else "w"
    with seeds_out.open(mode, encoding="utf-8") as f:
        if not args.append:
            f.write("# auto-generated from NOCTRIA_CORE_REQUIRED markers\n")
        for nid in node_ids:
            f.write(nid + "\n")

    with keep_out.open(mode, encoding="utf-8") as f:
        if not args.append:
            f.write("# auto-generated from NOCTRIA_CORE_REQUIRED markers\n")
        for sp in file_paths:
            f.write(sp + "\n")

    print(
        f"[ok] seeds -> {seeds_out}  count={len(node_ids)} (in_graph={sum(1 for i in node_ids if i in graph_id_set)})"
    )
    print(f"[ok] keep  -> {keep_out}   count={len(file_paths)}")


if __name__ == "__main__":
    main()
