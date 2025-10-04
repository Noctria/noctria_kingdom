#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cyto_build_overview.py
複数の *_hub.json（Cytoscape.js形式）をマージし、ステージ間の cluster→cluster エッジを付加して俯瞰ビュー JSON を出力。
"""

from __future__ import annotations
import argparse
import json
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Set

DEFAULT_CHAIN = [
    "collect",
    "analyze",
    "plan",
    "backtest",
    "forwardtest",
    "fintokei_check",
    "mt5_order",
    "settlement",
    "result_analyze",
    "merge_info",
    "replanning",
]


def load_cyto_json(p: Path) -> Dict:
    return json.loads(p.read_text(encoding="utf-8"))


def ensure_cluster_node(stage: str) -> Dict:
    cid = f"{stage}_cluster"
    return {"data": {"id": cid, "label": cid, "stage": stage}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--inputs",
        "-i",
        nargs="+",
        help="入力 JSON（*_hub.json）を複数指定。glob可。例: viz/graph_*_100_hub.json",
    )
    ap.add_argument("--output", "-o", required=True, help="出力 JSON パス")
    ap.add_argument(
        "--chain",
        "-c",
        default=",".join(DEFAULT_CHAIN),
        help="cluster間エッジを張るステージ順（カンマ区切り）。未指定は既定の11ステージ。",
    )
    ap.add_argument("--dedup", action="store_true", help="ノード/エッジの厳密重複を削除（推奨）")
    args = ap.parse_args()

    # 入力の展開（globを許容）
    patterns = args.inputs or []
    files: List[Path] = []
    for pat in patterns:
        files.extend([Path(p) for p in glob.glob(pat)])
    files = sorted({p.resolve() for p in files if p and Path(p).exists()})

    if not files:
        raise SystemExit("[err] no input files. pass with --inputs 'viz/graph_*_hub.json'")

    # マージ用の集合
    nodes_by_id: Dict[str, Dict] = {}
    edge_pairs: Set[Tuple[str, str]] = set()
    edges_out: List[Dict] = []

    total_nodes_in = 0
    total_edges_in = 0

    # 取り込み
    for p in files:
        data = load_cyto_json(p)
        elems = data.get("elements", {})
        nodes = elems.get("nodes", [])
        edges = elems.get("edges", [])
        total_nodes_in += len(nodes)
        total_edges_in += len(edges)
        # ノードは id キーでマージ
        for n in nodes:
            nid = n.get("data", {}).get("id")
            if not nid:
                continue
            if nid not in nodes_by_id:
                nodes_by_id[nid] = {"data": dict(n.get("data", {}))}
            else:
                # 既存と統合（label/stageが欠けていたら補完）
                d = nodes_by_id[nid]["data"]
                for k in ("label", "stage"):
                    if k not in d and n.get("data", {}).get(k) is not None:
                        d[k] = n["data"][k]
        # エッジは (source,target) で重複判定
        for e in edges:
            d = e.get("data", {})
            s, t = d.get("source"), d.get("target")
            if not s or not t:
                continue
            pair = (s, t)
            if (not args.dedup) or (pair not in edge_pairs):
                edge_pairs.add(pair)
                edges_out.append({"data": {"id": f"e{len(edges_out)}", "source": s, "target": t}})

    # チェーンに基づく cluster→cluster エッジを付与
    chain = [s.strip() for s in args.chain.split(",") if s.strip()]
    # クラスタノードが足りなければ追加
    for st in chain:
        cid = f"{st}_cluster"
        if cid not in nodes_by_id:
            nodes_by_id[cid] = ensure_cluster_node(st)

    # チェーンに沿って有向エッジ
    for a, b in zip(chain, chain[1:]):
        sa = f"{a}_cluster"
        tb = f"{b}_cluster"
        pair = (sa, tb)
        if (not args.dedup) or (pair not in edge_pairs):
            edge_pairs.add(pair)
            edges_out.append({"data": {"id": f"e{len(edges_out)}", "source": sa, "target": tb}})

    # 出力
    out_nodes = [{"data": dict(v["data"])} for v in nodes_by_id.values()]
    meta = {
        "in_files": [str(p) for p in files],
        "in_nodes_total": total_nodes_in,
        "in_edges_total": total_edges_in,
        "out_nodes": len(out_nodes),
        "out_edges": len(edges_out),
        "chain": chain,
    }
    out = {"elements": {"nodes": out_nodes, "edges": edges_out}, "meta": meta}

    Path(args.output).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] wrote {args.output} (nodes={len(out_nodes)}, edges={len(edges_out)})")


if __name__ == "__main__":
    main()
