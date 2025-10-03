#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
overlay_roles_to_mermaid.py (v4: label-first matching, legend fix)
- 役割パターンを「ノードID」だけでなく「ラベル（[...]の中身）」に優先してマッチ
- パスっぽいパターン（"src/plan_data/collector.py" 等）は basename に自動変換してラベルへ照合
- さらにフォールバックとして ID を“擬似パス復元”して緩く照合（__ → /, _ → [-_])
- 既存の manifest/spine もそのまま利用可
"""
from __future__ import annotations
import argparse, fnmatch, json, re
from pathlib import Path
from typing import Dict, List, Set

import yaml  # pip install PyYAML

NODE_RE = re.compile(r'^\s*([A-Za-z0-9_./:\-]+)\s*\[(.*?)\]\s*(?::[:A-Za-z0-9 _-]+)?$')

def parse_nodes(lines: List[str]) -> Dict[str, str]:
    """nodeId[Label] を dict へ"""
    nodes: Dict[str, str] = {}
    for ln in lines:
        m = NODE_RE.match(ln)
        if m:
            nid = m.group(1).strip()
            label = m.group(2).strip()
            # ラベルが ["file.py"] のように引用符付きなら外す
            if (label.startswith('"') and label.endswith('"')) or (label.startswith("'") and label.endswith("'")):
                label = label[1:-1]
            nodes[nid] = label
    return nodes

def _basename(glob: str) -> str:
    if "/" in glob:
        return glob.split("/")[-1]
    return glob

def _label_globs_from_pattern(pat: str) -> List[str]:
    base = _basename(pat)
    outs = []
    if "." not in base and "*" not in base and "?" not in base:
        outs.append(f"*{base}*")
    else:
        outs.append(base)
    return outs

def _pseudo_path_from_id(nid: str) -> str:
    s = nid.replace("__", "/")
    return s

def _id_regex_from_pattern(pat: str) -> re.Pattern:
    p = pat.replace("/", "__")
    esc = re.escape(p)
    esc = esc.replace(r"\*", ".*").replace(r"\?", ".")
    esc = esc.replace(r"\-", "[-_]").replace(r"\_", "[-_]")
    return re.compile(esc, re.IGNORECASE)

def match_roles(node_id: str, label: str, role_patterns: List[str]) -> bool:
    lab = label.lower()
    nid = node_id.lower()
    for pat in role_patterns:
        for g in _label_globs_from_pattern(pat.lower()):
            if fnmatch.fnmatch(lab, g):
                return True
    for pat in role_patterns:
        if fnmatch.fnmatch(lab, pat.lower()):
            return True
    pseudo = _pseudo_path_from_id(nid)
    for pat in role_patterns:
        rx = _id_regex_from_pattern(pat.lower())
        if rx.search(pseudo):
            return True
    return False

def ensure_styles(styles: Dict[str,str]) -> List[str]:
    out = ["", "%% ---- Auto-generated role styles ----"]
    styles = dict(styles or {})
    styles.setdefault("spine", "fill:#111827,stroke:#ef4444,stroke-width:3px,color:#ffffff")
    for cls, style in styles.items():
        out.append(f"classDef {cls} {style};")
    out.append("%% ------------------------------------")
    out.append("")
    return out

def build_stage_subgraphs(stage_order: List[str],
                          stage_titles: Dict[str,str],
                          node_classes: Dict[str,Set[str]]) -> List[str]:
    out: List[str] = ["", "%% ---- Stage subgraphs ----"]
    for st in stage_order or []:
        members = [nid for nid, cls in node_classes.items() if st in cls]
        if not members: continue
        title = stage_titles.get(st, st)
        out.append(f"subgraph {st}_cluster[\"{title}\"]")
        out.append("direction TB")
        for nid in sorted(members):
            out.append(f"{nid}")
        out.append("end")
    out.append("%% ---------------------------")
    out.append("")
    return out

def build_loop_arrows(stage_order: List[str]) -> List[str]:
    if not stage_order or len(stage_order) < 2: return []
    out = ["", "%% ---- Loop arrows ----"]
    pairs = list(zip(stage_order, stage_order[1:] + stage_order[:1]))
    for a,b in pairs:
        out.append(f"{a}_cluster --> {b}_cluster")
    out.append("%% ----------------------")
    out.append("")
    return out

def build_legend(styles: Dict[str,str], titles: Dict[str,str]) -> List[str]:
    out = ["", "%% ---- Legend (stage → color) ----", "subgraph legend[Legend]", "direction TB"]
    keys = list((styles or {}).keys()) + ["spine"]
    for st in sorted(set(keys)):
        title = titles.get(st, st) if titles else st
        nid   = f"legend_{st}"
        label = f"[{title}]"
        out.append(f"{nid}{label}")          # ノード定義
        out.append(f"class {nid} {st};")     # class 適用
    out.append("end")
    out.append("%% ---------------------------------")
    out.append("")
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--roles", required=True)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--spine-json", default=None)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    lines = Path(args.input).read_text(encoding="utf-8").splitlines()
    nodes = parse_nodes(lines)

    roles_cfg = yaml.safe_load(Path(args.roles).read_text(encoding="utf-8")) or {}
    roles: List[dict] = roles_cfg.get("roles", [])
    styles: Dict[str,str] = roles_cfg.get("styles", {}) or {}
    stage_order: List[str] = roles_cfg.get("stages_order", []) or []
    stage_titles: Dict[str,str] = roles_cfg.get("stage_titles", {}) or {}

    manifest = {}
    if args.manifest and Path(args.manifest).exists():
        manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8")) or {}

    node_classes: Dict[str, Set[str]] = {}
    for nid, label in nodes.items():
        for r in roles:
            cls = r.get("class_name")
            pats = r.get("patterns", []) or []
            if not cls or not pats:
                continue
            if match_roles(nid, label, pats):
                node_classes.setdefault(nid, set()).add(cls)

    for stage, files in (manifest.get("assign") or {}).items():
        for want in files or []:
            want_low = want.lower()
            for nid, label in nodes.items():
                lab = label.lower()
                if lab == want_low or lab.endswith("/"+want_low) or lab.endswith(want_low):
                    node_classes.setdefault(nid, set()).add(stage)
                    continue
            rx = _id_regex_from_pattern(want_low)
            for nid in nodes.keys():
                if rx.search(_pseudo_path_from_id(nid.lower())):
                    node_classes.setdefault(nid, set()).add(stage)

    if args.spine_json and Path(args.spine_json).exists():
        data = json.loads(Path(args.spine_json).read_text(encoding="utf-8"))
        for nid in data.keys():
            if nid in nodes:
                node_classes.setdefault(nid, set()).add("spine")

    out_lines = list(lines)
    out_lines += ensure_styles(styles)
    for nid, cls_set in sorted(node_classes.items()):
        out_lines.append(f"class {nid} {','.join(sorted(cls_set))};")

    if stage_order:
        out_lines += build_stage_subgraphs(stage_order, stage_titles, node_classes)
        out_lines += build_loop_arrows(stage_order)
    out_lines += build_legend(styles, stage_titles)

    Path(args.output).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"wrote: {args.output}")

if __name__ == "__main__":
    main()
