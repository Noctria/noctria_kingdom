#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
path_to_nodeid.py
- ファイルパスを "graph_mark_keep" 用のノードIDに変換して表示
- Seeds.txt に追記する時に使える補助ツール（重複はスキップ）

使い方:
    # 変換して表示だけ
    python tools/path_to_nodeid.py src/plan_data/analyzer.py

    # 変換して seeds.txt に追記（重複はスキップ）
    python tools/path_to_nodeid.py --add-seeds viz/seeds.txt src/plan_data/analyzer.py
"""

import sys
import os
from pathlib import Path


def normalize_path(path: str, project_root: str = "") -> str:
    """
    ファイルパスを node ID に変換する。

    例:
      src/plan_data/analyzer.py -> src_plan_data_analyzer_py
      noctria_gui/routes/observability.py -> noctria_gui_routes_observability_py
      airflow_docker/dags/noctria_kingdom_dag.py -> airflow_docker_dags_noctria_kingdom_dag_py
    """
    p = Path(path)
    s = str(p)

    # プロジェクトルートを除去
    if project_root and s.startswith(project_root):
        s = s[len(project_root):].lstrip("/")

    # 区切り "/" や "\" を "_" に置換
    s = s.replace("/", "_").replace("\\", "_")
    # ドットも "_" に置換（.py → _py）
    s = s.replace(".", "_")
    return s


def main():
    if len(sys.argv) < 2:
        print("Usage: path_to_nodeid.py [--add-seeds seeds.txt] <file1.py> [file2.py ...]")
        sys.exit(1)

    args = sys.argv[1:]
    add_seeds = None
    if args[0] == "--add-seeds":
        if len(args) < 3:
            print("Usage: path_to_nodeid.py --add-seeds seeds.txt <file1.py> ...")
            sys.exit(1)
        add_seeds = Path(args[1])
        paths = args[2:]
    else:
        paths = args

    project_root = os.environ.get("PROJECT_ROOT", "")

    results = []
    for path in paths:
        nid = normalize_path(path, project_root)
        print(f"{path} -> {nid}")
        results.append(nid)

    # seeds に追記（重複チェック）
    if add_seeds:
        add_seeds.parent.mkdir(parents=True, exist_ok=True)
        existing: set[str] = set()
        if add_seeds.exists():
            existing = {line.strip() for line in add_seeds.read_text(encoding="utf-8").splitlines() if line.strip()}

        new_entries = [nid for nid in results if nid not in existing]

        if new_entries:
            with add_seeds.open("a", encoding="utf-8") as f:
                for nid in new_entries:
                    f.write(nid + "\n")
            print(f"[ok] appended {len(new_entries)} new entries to {add_seeds}")
        else:
            print(f"[skip] all entries already exist in {add_seeds}")


if __name__ == "__main__":
    main()
