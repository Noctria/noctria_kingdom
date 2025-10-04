# tools/graph_mark_keep.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graph_mark_keep.py
- Cytoscape JSON + seedファイル（パスやID）から到達可能ノードを抽出
- KEEP / REMOVE候補 / MERGE候補（小粒・低次数）を分類
- レポート(Markdown)と各リスト、コアのみのサブグラフJSONを出力

想定ノード:
  node = {"data": {"id": "path_to_a_py", "label": "a.py", "stage": "plan", ...}}
想定エッジ:
  edge = {"data": {"id": "...", "source": "<id>", "target": "<id>"}}

ID突合ルール:
  - "パス→正規化ID": /mnt/d/noctria_kingdom/src/a/b.py → "src_a_b_py"
    （viewerのID生成に合わせるのが理想。必要なら調整）

使い方:
  python3 tools/graph_mark_keep.py \
    --graph viz/graph_overview_with_imports.json \
    --seeds viz/seeds.txt \
    --project-root /mnt/d/noctria_kingdom \
    --report viz/prune_plan.md \
    --keep-out viz/keep_list.txt \
    --remove-out viz/remove_candidates.txt \
    --merge-out viz/merge_candidates.txt \
    --subgraph-out viz/graph_core_only.json
"""

from __future__ import annotations
import argparse
import json
import os
import re
from pathlib import Path
from collections import deque, defaultdict
from typing import Dict, Set, List, Tuple


def norm_id_from_path(p: str, project_root: str) -> str:
    # パスからCytoscapeノードIDへの正規化（あなたのviewer側ルールに寄せる）
    p = os.path.abspath(p)
    if project_root and p.startswith(os.path.abspath(project_root) + os.sep):
        p = p[len(os.path.abspath(project_root)) + 1 :]
    # 例: noctria_gui/main.py → noctria_gui_main_py
    return re.sub(r"[^a-zA-Z0-9]+", "_", p).strip("_").lower()


def load_graph(graph_path: Path):
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = data.get("elements", {}).get("nodes", []) or data.get("nodes", [])
    edges = data.get("elements", {}).get("edges", []) or data.get("edges", [])
    # 標準化
    node_map: Dict[str, dict] = {}
    for n in nodes:
        d = n.get("data", n)
        if "id" in d:
            node_map[str(d["id"])] = {"data": d}
    adj_out: Dict[str, Set[str]] = defaultdict(set)
    adj_in: Dict[str, Set[str]] = defaultdict(set)
    for e in edges:
        d = e.get("data", e)
        s = str(d.get("source", ""))
        t = str(d.get("target", ""))
        if s and t and s in node_map and t in node_map:
            adj_out[s].add(t)
            adj_in[t].add(s)
    return node_map, adj_out, adj_in


def load_seed_ids(seed_file: Path, node_map: Dict[str, dict], project_root: str) -> Set[str]:
    seeds: Set[str] = set()
    for raw in seed_file.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        # 1) 既にIDとして合致
        if s in node_map:
            seeds.add(s)
            continue
        # 2) パスをID正規化して合致
        nid = norm_id_from_path(s, project_root)
        if nid in node_map:
            seeds.add(nid)
            continue
        # 3) ラベル一致（basename）
        base = os.path.basename(s).lower()
        found = [nid for nid, n in node_map.items() if n["data"].get("label", "").lower() == base]
        if found:
            seeds.update(found)
        else:
            # 見つからないが、とりあえず正規化IDを候補に追加（グラフ外の新規かも）
            # ただしここでは到達探索に使えないので無視
            pass
    return seeds


def bfs_reachable(starts: Set[str], adj_out: Dict[str, Set[str]]) -> Set[str]:
    seen: Set[str] = set()
    dq = deque(starts)
    while dq:
        u = dq.popleft()
        if u in seen:
            continue
        seen.add(u)
        for v in adj_out.get(u, ()):
            if v not in seen:
                dq.append(v)
    return seen


def degree_info(
    node_map: Dict[str, dict], adj_out: Dict[str, Set[str]], adj_in: Dict[str, Set[str]]
) -> Dict[str, Tuple[int, int, int]]:
    info = {}
    for nid in node_map:
        outd = len(adj_out.get(nid, ()))
        ind = len(adj_in.get(nid, ()))
        info[nid] = (ind, outd, ind + outd)
    return info


def guess_file_path(nid: str, project_root: str, node_map: Dict[str, dict]) -> str:
    # ノードの label がファイル名なら、それを手掛かりに推定（簡易）
    label = (node_map[nid]["data"].get("label") or "").strip()
    stage = node_map[nid]["data"].get("stage")
    # よくある拡張: .py, .html など
    candidates = []
    if label:
        candidates.append(label)
        if not label.endswith(
            (
                ".py",
                ".html",
                ".js",
                ".css",
                ".json",
                ".md",
                ".sql",
                ".yaml",
                ".yml",
                ".toml",
                ".ini",
                ".sh",
                ".bat",
                ".ps1",
                ".ts",
                ".tsx",
                ".vue",
                ".jinja",
                ".j2",
            )
        ):
            candidates.append(label + ".py")
    for c in candidates:
        p = Path(project_root) / c
        if p.exists():
            return str(p)
    # ダメなら stage フォルダで探索（簡易）
    if stage and label:
        candidate = Path(project_root) / stage / label
        if candidate.exists():
            return str(candidate)
    return ""  # 不明


def pick_merge_candidates(
    node_map, deg, project_root, size_kb_threshold=5, deg_sum_threshold=1
) -> List[str]:
    # とても小さくて次数も小さい＝“合併（集約）候補”
    out = []
    for nid, (_, _, tot) in deg.items():
        f = guess_file_path(nid, project_root, node_map)
        if not f or not os.path.isfile(f):
            continue
        try:
            size_kb = max(1, os.path.getsize(f) // 1024)
        except Exception:
            continue
        if size_kb <= size_kb_threshold and tot <= deg_sum_threshold:
            out.append(f)
    return sorted(set(out))


def write_subgraph(node_map, adj_out, keep: Set[str], out_path: Path):
    # KEEPだけの部分グラフJSONを書き出す
    nodes = [{"data": node_map[nid]["data"]} for nid in keep]
    edges = []
    for u in keep:
        for v in adj_out.get(u, ()):
            if v in keep:
                edges.append({"data": {"id": f"{u}->{v}", "source": u, "target": v}})
    data = {"elements": {"nodes": nodes, "edges": edges}}
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True, type=Path)
    ap.add_argument("--seeds", required=True, type=Path)
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--keep-out", required=True, type=Path)
    ap.add_argument("--remove-out", required=True, type=Path)
    ap.add_argument("--merge-out", required=True, type=Path)
    ap.add_argument("--subgraph-out", required=True, type=Path)
    args = ap.parse_args()

    node_map, adj_out, adj_in = load_graph(args.graph)
    seeds = load_seed_ids(args.seeds, node_map, args.project_root)
    if not seeds:
        raise SystemExit("No valid seeds found. Check seeds file/IDs.")

    keep = bfs_reachable(seeds, adj_out)
    all_ids = set(node_map.keys())
    remove_candidates = sorted(all_ids - keep)

    deg = degree_info(node_map, adj_out, adj_in)
    merge_candidates = pick_merge_candidates(node_map, deg, args.project_root)

    # ファイルパス化（KEEP/REMOVEはID中心、MERGEはファイルパス中心）
    keep_ids = sorted(keep)
    args.keep_out.write_text("\n".join(keep_ids) + "\n", encoding="utf-8")
    args.remove_out.write_text("\n".join(remove_candidates) + "\n", encoding="utf-8")
    args.merge_out.write_text("\n".join(merge_candidates) + "\n", encoding="utf-8")

    write_subgraph(node_map, adj_out, keep, args.subgraph_out)

    # Markdownレポート
    lines = []
    lines.append("# Prune Plan (Graph-based)")
    lines.append("")
    lines.append(f"- Graph: `{args.graph}`")
    lines.append(
        f"- Seeds: `{args.seeds}`  → KEEP={len(keep_ids)} / REMOVE候補={len(remove_candidates)}"
    )
    lines.append("")
    lines.append("## KEEP (IDs, reachability)")
    lines += [f"- {nid}" for nid in keep_ids[:200]]
    if len(keep_ids) > 200:
        lines.append(f"- ... (+{len(keep_ids)-200} more)")
    lines.append("")
    lines.append("## REMOVE candidates (IDs)")
    lines += [f"- {nid}" for nid in remove_candidates[:200]]
    if len(remove_candidates) > 200:
        lines.append(f"- ... (+{len(remove_candidates)-200} more)")
    lines.append("")
    lines.append("## MERGE candidates (small & low-degree files)")
    lines += [f"- {p}" for p in merge_candidates[:200]]
    if len(merge_candidates) > 200:
        lines.append(f"- ... (+{len(merge_candidates)-200} more)")
    lines.append("")
    lines.append("## Next")
    lines.append("- Review KEEP/REMOVE lists; edit seeds if needed.")
    lines.append("- Apply with tools/graph_prune_apply.py (generates commented bash).")
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
