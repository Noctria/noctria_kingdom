#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import sys
from collections import Counter

from src.core.path_config import ensure_import_path, STRATEGIES_VERITAS_GENERATED_DIR

ensure_import_path()
from src.codex.metrics_advanced import novelty_rate
from src.codex.obs_kpi import log_kpi


def _to_flat_float_list(v):
    try:
        if isinstance(v, dict):
            # キー昇順で値のみ（安定化）
            v = [v[k] for k in sorted(v.keys())]
        if not isinstance(v, (list, tuple)):
            return None
        out = []
        for x in v:
            if isinstance(x, (int, float)):
                out.append(float(x))
            else:
                return None  # ネスト/文字列は不採用
        return out if out else None
    except Exception:
        return None


def main() -> int:
    root = STRATEGIES_VERITAS_GENERATED_DIR
    if not root.exists():
        print("[kpi] no strategies dir; skip", file=sys.stderr)
        return 0

    pattern = os.environ.get("NOCTRIA_STRAT_GLOB", "*")
    dirs = [p for p in root.glob(pattern) if p.is_dir()]
    if not dirs:
        print(f"[kpi] no strategy dirs matched: {pattern}", file=sys.stderr)
        return 0

    rows, dropped = [], []
    for d in sorted(dirs):
        fv = d / "feature_vector.json"
        if not fv.exists():
            dropped.append(f"{d.name}:no_fv")
            continue
        try:
            raw = json.loads(fv.read_text(encoding="utf-8"))
        except Exception:
            dropped.append(f"{d.name}:bad_json")
            continue
        vec = _to_flat_float_list(raw)
        if not vec:
            dropped.append(f"{d.name}:not_flat_numeric")
            continue
        rows.append((d.name, vec))

    if len(rows) < 2:
        print(f"[kpi] insufficient vectors ({len(rows)}) ; dropped={dropped}", file=sys.stderr)
        return 0

    lens = Counter(len(v) for _, v in rows)
    target_len = max(lens.items(), key=lambda kv: kv[1])[0]
    used = [(n, v) for (n, v) in rows if len(v) == target_len]
    removed = [n for (n, v) in rows if len(v) != target_len]
    if len(used) < 2:
        print(f"[kpi] vectors filtered by length; still <2; removed={removed}", file=sys.stderr)
        return 0

    names = [n for (n, _) in used]
    vecs = [v for (_, v) in used]

    try:
        nv = novelty_rate(vecs)
    except Exception as e:
        print(f"[kpi] novelty_rate error: {e}", file=sys.stderr)
        return 0

    meta = {
        "n_total": len(rows),
        "n_used": len(used),
        "target_len": target_len,
        "removed": removed,
        "dropped": dropped,
        "names": names[:20],
    }
    log_kpi("Inventor", "novelty_rate", float(nv), meta)
    print(f"[kpi] novelty_rate={nv:.4f}  used={len(used)}/{len(rows)}  len={target_len}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
