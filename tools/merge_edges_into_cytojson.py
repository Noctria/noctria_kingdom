#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_edges_into_cytojson.py

既存の Cytoscape JSON（nodesのみ or star配線のみ）に、CSVの edge (source_path,target_path) を突合して追加。

CSV 形式:
    /abs/path/to/A.py,/abs/path/to/B.py
    ...

ノード ID の解決ルール（上から順に試行）:
  1) JSON の node.data.id と CSVパスの「正規化ID」が一致
  2) JSON の node.data.label(=basename) と CSVパスの basename が一致
  3) JSON の node.data.id が 「正規化ID」の末尾一致（安全な endswith）

拡張オプション:
  --strip-prefix "/mnt/d/noctria_kingdom/" : CSV 端末の絶対パスの先頭を剥がし、ID整合を取りやすくする
  --autocreate                              : 照合できない端点ノードを JSON に自動作成してからエッジを張る
  --stage-from-path "key:stage" ...         : 追加ノードの stage をパス断片から推定（最初にマッチしたものを採用）
                                              例: "airflow_docker:dags" "src:plan" "tests:analyze"
"""

from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Dict, List, Any


# ---------- 基本入出力 ----------
def load_cyto(path: Path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    elements = obj.get("elements", {})
    nodes = elements.get("nodes", [])
    edges = elements.get("edges", [])
    # elements が空ならトップを elements とみなす互換処理
    if not nodes and not edges and ("nodes" in obj or "edges" in obj):
        nodes = obj.get("nodes", [])
        edges = obj.get("edges", [])
        elements = {"nodes": nodes, "edges": edges}
        obj["elements"] = elements
    return obj, elements, nodes, edges


def build_index(nodes) -> tuple[Dict[str, Any], Dict[str, List[Any]]]:
    by_id: Dict[str, Any] = {}
    by_label: Dict[str, List[Any]] = {}
    for n in nodes:
        d = n.get("data", {})
        nid = str(d.get("id", "")) if d.get("id") is not None else ""
        lab = str(d.get("label", "")) if d.get("label") is not None else ""
        if nid:
            by_id[nid] = n
        if lab:
            by_label.setdefault(lab, []).append(n)
    return by_id, by_label


# ---------- ID 解決 ----------
def norm_id_from_path(p: str, strip_prefix: str | None = None) -> str:
    """
    パスを ID 文字列へ正規化:
      - 先頭 strip_prefix を剥がす（指定時のみ）
      - 先頭スラッシュ除去
      - スラ/ドットを '_' 置換
    例: /mnt/d/noctria_kingdom/src/core/logger.py
        -> mnt_d_noctria_kingdom_src_core_logger_py
    """
    s = p.replace("\\", "/")
    if strip_prefix:
        sp = strip_prefix.replace("\\", "/")
        if not sp.endswith("/"):
            sp += "/"
        if s.startswith(sp):
            s = s[len(sp) :]
    s = s.lstrip("/")
    s = s.replace(".", "_").replace("/", "_")
    return s


def resolve_node(csv_path: str, by_id, by_label, strip_prefix: str | None) -> str | None:
    nid = norm_id_from_path(csv_path, strip_prefix)
    # 1) 完全一致
    if nid in by_id:
        return nid
    # 2) label=basename 一致
    base = Path(csv_path).name
    if base in by_label:
        d = by_label[base][0].get("data", {})
        if d.get("id"):
            return str(d["id"])
    # 3) 末尾一致（具体性の高いものを優先）
    cands = [k for k in by_id.keys() if k.endswith(nid)]
    if cands:
        cands.sort(key=lambda x: -len(x))
        return cands[0]
    return None


# ---------- 追加ノード stage 推定 ----------
def parse_stage_rules(pairs: List[str]) -> List[tuple[str, str]]:
    rules: List[tuple[str, str]] = []
    for s in pairs:
        if ":" in s:
            key, st = s.split(":", 1)
            rules.append((key.strip(), st.strip()))
    return rules


def guess_stage(path: str, rules: List[tuple[str, str]]) -> str:
    low = path.lower()
    for key, st in rules:
        if key.lower() in low:
            return st
    return "unknown"


# ---------- メイン ----------
def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("nodes_json")
    ap.add_argument("edges_csv")
    ap.add_argument("out_json")
    ap.add_argument(
        "--strip-prefix",
        default="",
        help="CSV 絶対パスの先頭を剥がす（例: /mnt/d/noctria_kingdom/）",
    )
    ap.add_argument("--autocreate", action="store_true", help="未解決ノードを自動作成する")
    ap.add_argument(
        "--stage-from-path",
        nargs="*",
        default=[],
        help='例: "airflow_docker:dags" "src:plan" "tests:analyze"',
    )
    args = ap.parse_args()

    strip = args.strip_prefix or ""
    rules = parse_stage_rules(args.stage_from_path)

    nj, ecsv, out = Path(args.nodes_json), Path(args.edges_csv), Path(args.out_json)
    obj, elements, nodes, edges = load_cyto(nj)
    elements.setdefault("nodes", nodes)
    elements.setdefault("edges", edges)

    by_id, by_label = build_index(elements["nodes"])

    # 既存エッジの重複回避セット
    seen_pairs: set[tuple[str, str]] = set()
    for e in elements["edges"]:
        d = e.get("data", {})
        s, t = d.get("source"), d.get("target")
        if s and t:
            seen_pairs.add((str(s), str(t)))

    added_edges = 0
    added_nodes = 0
    skipped_unresolved = 0

    # 追加ノード作成
    def ensure_node_from_path(csv_path: str) -> str:
        nonlocal added_nodes
        nid = norm_id_from_path(csv_path, strip)
        if nid in by_id:
            return nid
        label = Path(csv_path).name
        stage = guess_stage(csv_path, rules)
        node_obj = {"data": {"id": nid, "label": label, "stage": stage}}
        elements["nodes"].append(node_obj)
        by_id[nid] = node_obj
        by_label.setdefault(label, []).append(node_obj)
        added_nodes += 1
        return nid

    # CSV を読んでマージ
    with ecsv.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 2:
                continue
            s_path, t_path = row[0].strip(), row[1].strip()
            s_id = resolve_node(s_path, by_id, by_label, strip)
            t_id = resolve_node(t_path, by_id, by_label, strip)

            # 見つからない端点はオプションで自動作成
            if args.autocreate:
                if s_id is None:
                    s_id = ensure_node_from_path(s_path)
                if t_id is None:
                    t_id = ensure_node_from_path(t_path)

            if s_id is None or t_id is None:
                skipped_unresolved += 1
                continue

            pair = (s_id, t_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            elements["edges"].append(
                {"data": {"id": f"e_merge_{len(seen_pairs)}", "source": s_id, "target": t_id}}
            )
            added_edges += 1

    # 出力
    obj["elements"] = elements
    meta = obj.get("meta", {})
    meta.update(
        {
            "merged_edges_added": added_edges,
            "merged_nodes_autocreated": added_nodes,
            "merge_skipped_unresolved": skipped_unresolved,
            "total_edges": len(elements["edges"]),
            "total_nodes": len(elements["nodes"]),
            "source_nodes_json": str(nj),
            "source_edges_csv": str(ecsv),
            "strip_prefix": strip,
            "stage_rules": rules,
        }
    )
    obj["meta"] = meta

    out.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    print(
        f"[ok] wrote {out}  +edges={added_edges}  +nodes={added_nodes}  "
        f"skipped={skipped_unresolved}  totals: nodes={len(elements['nodes'])} edges={len(elements['edges'])}"
    )


if __name__ == "__main__":
    main()
