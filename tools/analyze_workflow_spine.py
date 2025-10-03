#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_workflow_spine.py
- Mermaid(.mmd) のノード・エッジを読み取り、"メインストリーム（幹）"候補をスコアリング
- 指標:
  * fanin = 入次数（どれだけ参照されるか）→ 重み 2.0
  * fanout = 出次数 → 重み 1.0
  * stage_bridge = 異なるステージ間エッジの数（roles overlay 後のクラス指定を利用）→ 重み 1.5
  * entrypoint_flags = 入口/実行点っぽさ（ファイル名/パス名ヒューリスティクス）→ +0.5〜+1.0
- 出力:
  * JSON: {node_id: {"score": float, "fanin": int, "fanout": int, "stage_bridges": int, "flags":[...]}, ...}
  * Markdown: 上位N件の表
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Dict, List, Tuple, Set

NODE_RE = re.compile(r'^\s*([A-Za-z0-9_./:\-]+)\s*\[(.*?)\]\s*$')
EDGE_RE = re.compile(r'^\s*([A-Za-z0-9_./:\-]+)\s*[-.]{1,2}>\s*([A-Za-z0-9_./:\-]+)\s*$')
CLASS_RE = re.compile(r'^\s*class\s+([A-Za-z0-9_./:\-]+)\s+([A-Za-z0-9_,\-]+);')

def parse_mmd(path: Path) -> Tuple[Dict[str,str], List[Tuple[str,str]], Dict[str,Set[str]]]:
    nodes: Dict[str,str] = {}
    edges: List[Tuple[str,str]] = []
    classes: Dict[str,Set[str]] = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = NODE_RE.match(ln)
        if m:
            nodes[m.group(1)] = m.group(2)
            continue
        m = EDGE_RE.match(ln)
        if m:
            edges.append((m.group(1), m.group(2)))
            continue
        m = CLASS_RE.match(ln)
        if m:
            nid = m.group(1); cls = m.group(2).split(",")
            classes.setdefault(nid, set()).update([c.strip() for c in cls if c.strip()])
    return nodes, edges, classes

ENTRY_HINTS = (
    "main.py", "run_", "execute_", "runner", "orchestrator", "pdca", "dag", "routes",
    "server", "app.py", "mt5", "order", "settle", "backtest", "forward"
)

def entrypoint_bonus(node_id: str) -> Tuple[float, List[str]]:
    bonus = 0.0; flags: List[str] = []
    low = node_id.lower()
    for key in ENTRY_HINTS:
        if key in low:
            b = 1.0 if key in ("orchestrator","server","app.py","dag") else 0.5
            bonus += b
            flags.append(f"hint:{key}")
    return min(bonus, 2.0), flags  # 上限

def analyze(mmd_path: Path, topk: int = 30) -> Dict[str, dict]:
    nodes, edges, classes = parse_mmd(mmd_path)
    fanin = {n:0 for n in nodes}
    fanout= {n:0 for n in nodes}
    for a,b in edges:
        if a in nodes: fanout[a]+=1
        if b in nodes: fanin[b]+=1

    # ステージ（roles）取得
    def get_stage_set(nid:str)->Set[str]:
        return set(c for c in classes.get(nid, set()) if c not in ("spine","gui","docs","airflow","pdca","plan","do","check","act")
                   or c in ("collect","analyze","plan","backtest","forwardtest","fintokei_check","mt5_order","settlement","result_analyze","merge_info","replanning"))

    stage_bridges = {n:0 for n in nodes}
    for a,b in edges:
        sa, sb = get_stage_set(a), get_stage_set(b)
        if sa and sb and sa.isdisjoint(sb):
            if a in nodes: stage_bridges[a]+=1
            if b in nodes: stage_bridges[b]+=1

    scores: Dict[str, dict] = {}
    for n in nodes:
        fanin_w, fanout_w, bridge_w = 2.0, 1.0, 1.5
        bonus, flags = entrypoint_bonus(n)
        score = fanin[n]*fanin_w + fanout[n]*fanout_w + stage_bridges[n]*bridge_w + bonus
        scores[n] = {
            "score": round(score, 3),
            "fanin": fanin[n],
            "fanout": fanout[n],
            "stage_bridges": stage_bridges[n],
            "flags": flags
        }

    # 上位 topk
    ranked = dict(sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)[:topk])
    return ranked

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="mmd after roles overlay (or raw)")
    ap.add_argument("--json_out", required=True)
    ap.add_argument("--md_out", required=True)
    ap.add_argument("--topk", type=int, default=30)
    args = ap.parse_args()

    ranked = analyze(Path(args.input), topk=args.topk)

    Path(args.json_out).write_text(json.dumps(ranked, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown出力
    lines = ["# Workflow Spine (Top {})".format(len(ranked)),
             "",
             "| rank | node | score | fanin | fanout | stage_bridges | flags |",
             "|---:|---|---:|---:|---:|---:|---|"]
    for i,(n,met) in enumerate(sorted(ranked.items(), key=lambda kv: kv[1]["score"], reverse=True), start=1):
        lines.append(f"| {i} | `{n}` | {met['score']} | {met['fanin']} | {met['fanout']} | {met['stage_bridges']} | {', '.join(met['flags'])} |")
    Path(args.md_out).write_text("\n".join(lines)+"\n", encoding="utf-8")

    print(f"wrote: {args.json_out}")
    print(f"wrote: {args.md_out}")

if __name__ == "__main__":
    main()
