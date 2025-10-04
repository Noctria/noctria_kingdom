#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任意のグラフJSONを Cytoscape.js 標準形に正規化する
入力側の想定バリエーション:
- { "elements": { "nodes":[{...}|{"data":{...}}], "edges":[{...}|{"data":{...}}] }, "meta": ... }
- { "nodes":[...], "edges":[...] }
- [ {...}, {...}, ... ]  # data付きノード配列 or group指定配列 など
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Dict


def to_cyto_elements(obj: Any) -> Dict[str, Any]:
    # 1) elements 抽出
    elements = None
    if isinstance(obj, dict) and "elements" in obj:
        elements = obj["elements"]
    elif isinstance(obj, dict) and ("nodes" in obj or "edges" in obj):
        elements = {"nodes": obj.get("nodes", []), "edges": obj.get("edges", [])}
    elif isinstance(obj, list):
        # groupやsource/targetの有無で推定
        nodes = []
        edges = []
        for x in obj:
            if isinstance(x, dict) and (
                "source" in x or (isinstance(x.get("data"), dict) and "source" in x["data"])
            ):
                edges.append(x)
            else:
                nodes.append(x)
        elements = {"nodes": nodes, "edges": edges}
    else:
        elements = {"nodes": [], "edges": []}

    def norm_node(n: Any) -> Dict[str, Any]:
        d = dict(n.get("data", {})) if isinstance(n, dict) else {}
        # トップに id/label がある場合は拾う
        if isinstance(n, dict):
            if "id" in n and "id" not in d:
                d["id"] = n["id"]
            if "label" in n and "label" not in d:
                d["label"] = n["label"]
            if "stage" in n and "stage" not in d:
                d["stage"] = n["stage"]
        if "id" in d:
            d["id"] = str(d["id"])
        if "label" in d:
            d["label"] = str(d["label"])
        return {"data": d}

    eid = 0

    def norm_edge(e: Any) -> Dict[str, Any]:
        nonlocal eid
        d = dict(e.get("data", {})) if isinstance(e, dict) else {}
        if isinstance(e, dict):
            if "source" in e and "source" not in d:
                d["source"] = e["source"]
            if "target" in e and "target" not in d:
                d["target"] = e["target"]
            if "id" in e and "id" not in d:
                d["id"] = e["id"]
        if "id" not in d:
            d["id"] = f"e{eid}"
            eid += 1
        if "source" in d:
            d["source"] = str(d["source"])
        if "target" in d:
            d["target"] = str(d["target"])
        return {"data": d}

    nodes = [norm_node(n) for n in elements.get("nodes", [])]
    edges = [norm_edge(e) for e in elements.get("edges", [])]

    return {"elements": {"nodes": nodes, "edges": edges}}


def main():
    if len(sys.argv) < 3:
        print("Usage: cyto_normalize_anyjson.py <input.json> <output.json>", file=sys.stderr)
        sys.exit(2)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    obj = json.loads(src.read_text(encoding="utf-8"))
    norm = to_cyto_elements(obj)
    meta = obj.get("meta", {}) if isinstance(obj, dict) else {}
    out = {**norm, "meta": meta}
    dst.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(
        f"[ok] wrote {dst}  nodes={len(norm['elements']['nodes'])}  edges={len(norm['elements']['edges'])}"
    )


if __name__ == "__main__":
    main()
