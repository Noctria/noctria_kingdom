#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path


def main(in_json, out_json, stage):
    data = json.loads(Path(in_json).read_text(encoding="utf-8"))
    elems = data.get("elements", {})
    nodes = elems.get("nodes", [])
    edges = elems.get("edges", [])

    # 既存のハブ候補: "<stage>_cluster"
    hub_id = f"{stage}_cluster"

    node_ids = {n["data"]["id"] for n in nodes}
    # ハブが無ければ追加
    if hub_id not in node_ids:
        nodes.append({"data": {"id": hub_id, "label": hub_id, "stage": stage}})
        node_ids.add(hub_id)

    # すでにあるエッジIDの最大インデックスを探す
    max_i = -1
    for e in edges:
        try:
            i = int(str(e["data"]["id"]).lstrip("e"))
            if i > max_i:
                max_i = i
        except Exception:
            pass
    i = max_i + 1

    # 同ステージノードをハブにスター接続
    added = 0
    for n in nodes:
        d = n.get("data", {})
        if d.get("stage") == stage and d.get("id") != hub_id:
            edges.append({"data": {"id": f"e{i}", "source": hub_id, "target": d["id"]}})
            i += 1
            added += 1

    data["elements"]["nodes"] = nodes
    data["elements"]["edges"] = edges
    meta = data.setdefault("meta", {})
    meta[f"attached_{stage}_hub_edges"] = added

    Path(out_json).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] wrote {out_json} (added {added} hub edges to {hub_id})")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python tools/cyto_attach_stage_hub.py <in.json> <out.json> <stage>")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
