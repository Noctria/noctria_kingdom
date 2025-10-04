#!/usr/bin/env python3
# coding: utf-8
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import List, Tuple
import numpy as np
import matplotlib.pyplot as plt


def load_meta(meta_path: Path):
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    y_prob = meta.get("y_prob") or meta.get("predicted_prob")
    y_true = meta.get("y_true") or meta.get("labels")
    return y_prob, y_true


def list_run_dirs(root: Path, limit: int | None) -> List[Path]:
    if (root / "meta.json").exists():
        return [root]
    runs = [p for p in root.glob("run_*") if (p / "meta.json").exists()]
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs if limit is None else runs[:limit]


def reliability_curve(
    y_prob: np.ndarray, y_true: np.ndarray, bins: int = 10
) -> Tuple[np.ndarray, np.ndarray]:
    edges = np.linspace(0, 1, bins + 1)
    confs, accs = [], []
    for i in range(bins):
        m = (y_prob >= edges[i]) & (
            y_prob < edges[i + 1] if i < bins - 1 else y_prob <= edges[i + 1]
        )
        if np.any(m):
            confs.append(float(np.mean(y_prob[m])))
            accs.append(float(np.mean((y_prob[m] >= 0.5).astype(int) == y_true[m])))
    return np.array(confs, float), np.array(accs, float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--reports", default="reports/veritas", help="run_* 親 or 特定 run ディレクトリ"
    )
    ap.add_argument("--limit", type=int, default=3, help="最新N runを描画（親指定時）")
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--out", default=None, help="保存パス（未指定なら各run下に保存）")
    args = ap.parse_args()

    root = Path(args.reports)
    runs = list_run_dirs(root, args.limit)
    if not runs:
        print(f"[plot] no meta.json under {root}")
        return 0

    for run_dir in runs:
        meta_path = run_dir / "meta.json"
        y_prob, y_true = load_meta(meta_path)
        if not (
            isinstance(y_prob, list)
            and isinstance(y_true, list)
            and len(y_prob) == len(y_true)
            and len(y_true) >= 5
        ):
            print(f"[plot] skip {run_dir.name} (insufficient arrays)")
            continue

        yp = np.asarray(y_prob, float)
        yt = np.asarray(y_true, int)
        confs, accs = reliability_curve(yp, yt, bins=args.bins)

        plt.figure()
        plt.plot([0, 1], [0, 1], linestyle="--", label="perfect")
        plt.plot(confs, accs, marker="o", label=run_dir.name)
        plt.xlabel("Mean confidence")
        plt.ylabel("Empirical accuracy")
        plt.title(f"Reliability: {run_dir.name}")
        plt.legend()
        out = Path(args.out) if args.out else (run_dir / "reliability.png")
        plt.tight_layout()
        plt.savefig(out)
        plt.close()
        print(f"[plot] saved {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
