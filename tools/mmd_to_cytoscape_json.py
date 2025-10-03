#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/mmd_to_cytoscape_json.py
Mermaid(.mmd) → Cytoscape.js 互換 JSON 変換 + 診断 (--debug)
"""
from __future__ import annotations

import argparse, json, re
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Set, Iterable

# ====== トークンとブロック ======
QID   = r'"[^"\r\n]+"'                          # " ... "
NQID  = r'[A-Za-z0-9_:\-./\\+@]+(?:\s+[A-Za-z0-9_:\-./\\+@]+)*'
IDTOK = rf'(?:{QID}|{NQID})'
LBL   = r'(?:\[[^\]]*\]|\([^)]+\)|\{[^}]+\}|\[\[[^\]]*\]\]|\(\([^)]+\)\)|\{\{[^}]+\}\})'

# ====== 無視する行（先頭） ======
RE_GRAPH    = re.compile(r'^\s*graph\s+\w+', re.I)
RE_CLASSDEF = re.compile(r'^\s*classDef\s+', re.I)
RE_SUBGRAPH = re.compile(r'^\s*subgraph\b', re.I)
RE_END      = re.compile(r'^\s*end\s*$', re.I)
RE_CHEAD    = re.compile(r'^\s*%%')

# ====== 行パターン ======
RE_NODE = re.compile(
    rf'^\s*(?P<id>{IDTOK})\s*(?P<label>{LBL})?\s*(?:::+\s*(?P<class>[A-Za-z0-9_:\-./\\+@]+))?\s*;?\s*$'
)
# エッジ演算子（代表形）
OP = r'(?:-->|---|-\.\->|==>|--|--o|o--|--x|x--)'

# 1マッチ分のエッジ (src [lbl] [:::class]) OP (dsts [lbl] [:::class])
RE_EDGE_ONE = re.compile(
    rf'(?P<src>{IDTOK})\s*(?P<src_lbl>{LBL})?\s*(?:::+\s*(?P<src_cls>[A-Za-z0-9_:\-./\\+@]+))?\s*'
    rf'(?P<op>{OP})\s*'
    rf'(?P<dsts>{IDTOK}(?:\s*&\s*{IDTOK})*)\s*(?P<dst_lbl>{LBL})?\s*(?:::+\s*(?P<dst_cls>[A-Za-z0-9_:\-./\\+@]+))?'
)

# class 行
RE_CLASS = re.compile(
    rf'^\s*class\s+(?P<ids>{IDTOK}(?:\s*,\s*{IDTOK})*)\s+(?P<class>[A-Za-z0-9_:\-./\\+@]+)\s*;?\s*$'
)

# ====== ヘルパ ======
def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == '"': return s[1:-1]
    if len(s) >= 2 and s[0] == s[-1] == "'": return s[1:-1]
    return s

def _norm_id(tok: str) -> str:
    return _strip_quotes(tok.strip())

def _extract_label(raw: str | None) -> str | None:
    if not raw: return None
    s = raw.strip()
    if s.startswith("[[") and s.endswith("]]"): inner = s[2:-2].strip()
    elif s.startswith("((") and s.endswith("))"): inner = s[2:-2].strip()
    elif s.startswith("{{") and s.endswith("}}"): inner = s[2:-2].strip()
    elif s[0] in "[({" and s[-1] in "])}":       inner = s[1:-1].strip()
    else: inner = s
    return _strip_quotes(inner)

def _tokenize_ids(csv_like: str) -> List[str]:
    return [_norm_id(p) for p in [t.strip() for t in csv_like.split(",")] if p]

def _split_and_ids(s: str) -> List[str]:
    return [_norm_id(p) for p in re.split(r'\s*&\s*', s) if p.strip()]

def _read_lines(path: Path) -> Iterable[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for ln in text.splitlines():
        if RE_CHEAD.match(ln): continue
        core = ln.split("%%", 1)[0]             # 行内コメント除去
        if not core.strip(): continue
        if RE_GRAPH.match(core) or RE_CLASSDEF.match(core): continue
        yield core.rstrip()

def _pre_edge(s: str) -> str:
    # |...| を除去
    s = re.sub(r'\|[^|]*\|', ' ', s)
    # '-- text -->' の text を除去
    s = re.sub(r'--\s+[^-][^>]*?-->', '-->', s)
    # 代表形寄せ
    s = re.sub(r'-\s*\.\s*-\s*>', '-.->', s)
    s = re.sub(r'={2,}\s*>', '==>', s)
    s = re.sub(r'-{3,}\s*>', '-->', s)
    s = re.sub(r'\s---\s', ' --> ', s)
    s = re.sub(r'-{2}(?!>)', '--', s)
    return s

# ====== 解析 ======
def parse_mmd(lines: Iterable[str], debug: bool=False, dbg_limit: int=20) -> Tuple[Dict[str, Dict], List[Tuple[str, str]], Dict[str, str]]:
    nodes: Dict[str, Dict] = {}
    edges: List[Tuple[str, str]] = []
    node_stage: Dict[str, str] = {}
    # デバッグ統計
    cand_edges = 0
    matched_edges = 0
    unmatched_samples: List[str] = []

    for raw in lines:
        line = raw.strip()
        if not line: continue
        if RE_SUBGRAPH.match(line) or RE_END.match(line):
            # subgraph/end は構造用、無視（必要なら後で使う）
            continue

        # class 行
        m = RE_CLASS.match(line)
        if m:
            ids = _tokenize_ids(m.group("ids"))
            stage = m.group("class")
            for nid in ids:
                node_stage[nid] = stage
                if nid in nodes:
                    nodes[nid]["stage"] = stage
            continue

        # ノード行
        m = RE_NODE.match(line)
        if m:
            nid = _norm_id(m.group("id"))
            label = _extract_label(m.group("label")) or nid
            cls = m.group("class")
            cur = nodes.get(nid, {"id": nid})
            cur["label"] = label or cur.get("label", nid)
            if cls:
                cur["stage"] = cls
                node_stage[nid] = cls
            nodes[nid] = cur
            continue

        # エッジ候補かざっくり判定
        if any(op in line for op in ['--', '->', '==>']):
            cand_edges += 1
            prep = _pre_edge(line)
            # 1行に複数マッチ（A-->B-->C）も拾う
            found = False
            for em in RE_EDGE_ONE.finditer(prep):
                found = True
                src    = _norm_id(em.group("src"))
                dsts   = _split_and_ids(em.group("dsts"))
                srccls = em.group("src_cls")
                dstcls = em.group("dst_cls")
                if src not in nodes:
                    nodes[src] = {"id": src, "label": src}
                if srccls:
                    nodes[src]["stage"] = srccls
                    node_stage[src] = srccls
                for dst in dsts:
                    if dst not in nodes:
                        nodes[dst] = {"id": dst, "label": dst}
                    if dstcls:
                        nodes[dst]["stage"] = dstcls
                        node_stage[dst] = dstcls
                    edges.append((src, dst))
                    matched_edges += 1
            if not found and debug and len(unmatched_samples) < dbg_limit:
                unmatched_samples.append(line)
            continue

        # それ以外は無視

    # class でのみ出たノードを補完
    for nid, st in node_stage.items():
        if nid not in nodes:
            nodes[nid] = {"id": nid, "label": nid, "stage": st}
        else:
            nodes[nid].setdefault("stage", st)

    if debug:
        print(f"[debug] candidate edge lines: {cand_edges}")
        print(f"[debug] matched edge segments: {matched_edges}")
        if unmatched_samples:
            print("[debug] unmatched edge-like lines (samples):")
            for s in unmatched_samples:
                print("  -", s[:300])

    return nodes, edges, node_stage

# ====== サブセット・制限 ======
def largest_connected_component(nodes: Dict[str, Dict], edges: List[Tuple[str, str]]) -> Set[str]:
    if not nodes: return set()
    adj: Dict[str, Set[str]] = defaultdict(set)
    for s, t in edges: adj[s].add(t); adj[t].add(s)
    visited: Set[str] = set(); best: Set[str] = set()
    for start in nodes.keys():
        if start in visited: continue
        comp: Set[str] = {start}
        q = deque([start]); visited.add(start)
        while q:
            u = q.popleft()
            for v in adj.get(u, []):
                if v not in visited:
                    visited.add(v); comp.add(v); q.append(v)
        if len(comp) > len(best): best = comp
    return best

def subset_by_stage(nodes: Dict[str, Dict], edges: List[Tuple[str, str]], stage: str | None):
    if not stage: return nodes, edges
    keep = {nid for nid, d in nodes.items() if d.get("stage") == stage}
    n2 = {nid: nodes[nid] for nid in keep}
    e2 = [(s, t) for (s, t) in edges if s in keep and t in keep]
    return n2, e2

def limit_nodes(nodes: Dict[str, Dict], edges: List[Tuple[str, str]], limit: int | None):
    if not limit or limit <= 0 or len(nodes) <= limit: return nodes, edges
    deg = defaultdict(int)
    for s, t in edges: deg[s]+=1; deg[t]+=1
    ordered = sorted(nodes.keys(), key=lambda nid: (-deg[nid], nodes[nid].get("label","")))
    keep = set(ordered[:limit])
    n2 = {nid: nodes[nid] for nid in keep}
    e2 = [(s, t) for (s, t) in edges if s in keep and t in keep]
    return n2, e2

# ====== 出力 ======
def to_cytoscape_json(nodes: Dict[str, Dict], edges: List[Tuple[str, str]], meta: Dict) -> Dict:
    elems_nodes = [{"data": {"id": nid, "label": d.get("label", nid), "stage": d.get("stage", "")}} for nid, d in nodes.items()]
    elems_edges = [{"data": {"id": f"e{i}", "source": s, "target": t}} for i, (s, t) in enumerate(edges)]
    return {"elements": {"nodes": elems_nodes, "edges": elems_edges}, "meta": meta}

# ====== CLI ======
def main():
    ap = argparse.ArgumentParser(description="Convert Mermaid .mmd to Cytoscape.js JSON (with robust edge parsing & debug)")
    ap.add_argument("--input","-i", required=True)
    ap.add_argument("--output","-o", required=True)
    ap.add_argument("--stage","-s", default=None)
    ap.add_argument("--limit","-n", type=int, default=0)
    ap.add_argument("--component", action="store_true")
    ap.add_argument("--debug", action="store_true", help="print diagnostics for edge parsing")
    ap.add_argument("--debug-samples", type=int, default=20, help="max unmatched samples to print")
    args = ap.parse_args()

    lines = _read_lines(Path(args.input))
    nodes, edges, _ = parse_mmd(lines, debug=args.debug, dbg_limit=args.debug_samples)
    total_nodes, total_edges = len(nodes), len(edges)

    nodes, edges = subset_by_stage(nodes, edges, args.stage)

    if args.component and nodes:
        keep = largest_connected_component(nodes, edges)
        edges = [(s, t) for (s, t) in edges if s in keep and t in keep]
        nodes = {nid: d for nid, d in nodes.items() if nid in keep}

    nodes, edges = limit_nodes(nodes, edges, args.limit)

    meta = {
        "source": str(args.input),
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "out_nodes": len(nodes),
        "out_edges": len(edges),
        "stage": args.stage or "",
        "limited": int(args.limit or 0),
        "largest_component_only": bool(args.component),
    }
    Path(args.output).write_text(json.dumps(to_cytoscape_json(nodes, edges, meta), ensure_ascii=False), encoding="utf-8")
    print(f"[ok] wrote {args.output} (nodes={meta['out_nodes']}, edges={meta['out_edges']})")

if __name__ == "__main__":
    main()
