#!/usr/bin/env python3
# coding: utf-8
from __future__ import annotations
import os, json, argparse
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
import psycopg2

# --- env / DSN ---
DSN = os.getenv("NOCTRIA_OBS_PG_DSN", "postgresql://noctria:noctria@127.0.0.1:5432/noctria_db")

# --- metrics ---
def brier_score(y_prob: np.ndarray, y_true: np.ndarray) -> float:
    y_prob = np.asarray(y_prob, dtype=float).ravel()
    y_true = np.asarray(y_true, dtype=int).ravel()
    return float(np.mean((y_prob - y_true) ** 2))

def ece_calibration(y_prob: np.ndarray, y_true: np.ndarray, bins: int = 10) -> float:
    y_prob = np.asarray(y_prob, dtype=float).ravel()
    y_true = np.asarray(y_true, dtype=int).ravel()
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    N = len(y_prob)
    for i in range(bins):
        if i < bins - 1:
            m = (y_prob >= edges[i]) & (y_prob < edges[i + 1])
        else:
            m = (y_prob >= edges[i]) & (y_prob <= edges[i + 1])
        if not np.any(m):
            continue
        conf = float(np.mean(y_prob[m]))
        acc  = float(np.mean((y_prob[m] >= 0.5).astype(int) == y_true[m]))
        ece += (np.sum(m) / N) * abs(acc - conf)
    return float(ece)

# --- db ---
def insert_kpi(cur, agent: str, metric: str, value: float, meta: Optional[dict] = None):
    cur.execute(
        """
        INSERT INTO obs_codex_kpi(agent, metric, value, created_at, meta)
        VALUES (%s, %s, %s, NOW(), COALESCE(%s::jsonb, '{}'::jsonb))
        """,
        (agent, metric, value, json.dumps(meta or {})),
    )

# --- io / helpers ---
def _load_meta(meta_path: Path) -> Dict[str, Any]:
    """meta.json を dict で返す（配列だった古い形式にも防御）"""
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = data[-1] if data and isinstance(data[-1], dict) else {}
    return data if isinstance(data, dict) else {}

def _extract_arrays(meta: Dict[str, Any]) -> Tuple[Optional[List[float]], Optional[List[int]], List[bool], Dict[str, Any]]:
    # 後方互換キー対応
    y_prob = meta.get("y_prob") or meta.get("predicted_prob")
    y_true = meta.get("y_true") or meta.get("labels")
    adv    = meta.get("adv_results", []) or []
    calib  = meta.get("calibration") or {}
    return y_prob, y_true, adv, calib if isinstance(calib, dict) else {}

def _resolve_targets(reports_arg: Path, limit: Optional[int]) -> List[Path]:
    """
    対応パターン:
      - 親: reports/veritas -> 直近 run_* を limit 件
      - run: reports/veritas/run_YYYY... -> その1件
      - 直指定: .../meta.json -> その1件
    返り値は meta.json ファイルパスの配列
    """
    p = reports_arg
    if p.is_file():
        # 直指定（meta.json）
        return [p]

    # run ディレクトリ（中に meta.json がある）
    if (p / "meta.json").exists():
        return [p / "meta.json"]

    # 親ディレクトリ
    cands = sorted(p.glob("run_*/meta.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    if limit:
        cands = cands[: max(1, int(limit))]
    else:
        cands = cands[:1] if cands else []
    return cands

def _bins_from_meta_or_arg(calib: Dict[str, Any], arg_bins: Optional[int]) -> int:
    if isinstance(calib.get("bins"), (int, float)) and int(calib["bins"]) > 0:
        return int(calib["bins"])
    if isinstance(arg_bins, int) and arg_bins > 0:
        return arg_bins
    return 10

def _run_id_from(meta: Dict[str, Any], meta_path: Path) -> str:
    if isinstance(meta.get("run_id"), str) and meta["run_id"]:
        return meta["run_id"]
    # parent dir が run_* の時
    try:
        return meta_path.parent.name
    except Exception:
        return "unknown_run"

def process_one_meta(meta_path: Path, agent: str, default_bins: Optional[int], conn) -> None:
    meta = _load_meta(meta_path)
    y_prob, y_true, adv, calib = _extract_arrays(meta)

    run_id = _run_id_from(meta, meta_path)
    bins   = _bins_from_meta_or_arg(calib, default_bins)

    base_meta = {
        "report": str(meta_path.parent),
        "run_id": run_id,
        "calibration": calib,
    }

    # 校正系
    ok_arrays = (isinstance(y_prob, list) and isinstance(y_true, list)
                 and len(y_prob) == len(y_true) and len(y_true) >= 5)
    if ok_arrays:
        yp = np.array(y_prob, float)
        yt = np.array(y_true, int)
        bs  = brier_score(yp, yt)
        ece = ece_calibration(yp, yt, bins=bins)
        with conn.cursor() as cur:
            insert_kpi(cur, agent, "brier_score",     float(bs),  base_meta)
            insert_kpi(cur, agent, "ece_calibration", float(ece), base_meta)
        print(f"[kpi] {run_id} brier={bs:.4f} ece={ece:.4f} (bins={bins})")
    else:
        print(f"[kpi] calibration skipped for {run_id} (no/short y_prob,y_true)")

    # 逆境耐性
    if isinstance(adv, list) and len(adv) > 0:
        adv_rate = float(np.mean([1.0 if bool(v) else 0.0 for v in adv]))
        with conn.cursor() as cur:
            insert_kpi(cur, agent, "adversarial_pass_rate", adv_rate, base_meta)
        print(f"[kpi] {run_id} adversarial_pass_rate={adv_rate:.3f}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default="reports/veritas",
                    help="reports root（例: reports/veritas）/ run ディレクトリ / meta.json のいずれか")
    ap.add_argument("--agent",   default="Prometheus")
    ap.add_argument("--limit",   type=int, default=None,
                    help="親ディレクトリ指定時に処理する最新 run 件数（省略時は最新1件）")
    ap.add_argument("--bins",    type=int, default=None,
                    help="ECE のビン数（meta.calibration.bins があればそちらを優先）")
    args = ap.parse_args()

    targets = _resolve_targets(Path(args.reports), args.limit)
    if not targets:
        print(f"[kpi] no meta.json found under {args.reports}; nothing to log")
        return 0

    with psycopg2.connect(DSN) as conn:
        for meta_path in targets:
            try:
                process_one_meta(meta_path, agent=args.agent, default_bins=args.bins, conn=conn)
            except Exception as e:
                print(f"[kpi] error on {meta_path}: {e}")
        conn.commit()

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
