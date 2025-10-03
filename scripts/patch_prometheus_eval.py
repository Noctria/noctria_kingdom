#!/usr/bin/env python3
# coding: utf-8
"""
Patch evaluate_veritas.py to log y_prob/labels to reports, apply temperature scaling,
and run a minimal adversarial suite. Idempotent (safe to run multiple times).
"""

from __future__ import annotations
import re, sys
from pathlib import Path

TARGET = Path("src/veritas/evaluate_veritas.py")

IMPORTS = """\
import datetime as dt
import numpy as np
"""

HELPERS = """\
REPORTS_BASE = Path("reports") / "veritas"

# ---- optional helpers (temperature scaling & adversarial) ----
try:
    # scipy が無ければ T=1.0 を返す安全版
    from scipy.optimize import minimize
except Exception:
    minimize = None

def _temperature_scale(logits: np.ndarray, y_true: np.ndarray) -> float:
    if minimize is None:
        return 1.0
    logits = np.asarray(logits, dtype=float).ravel()
    y_true = np.asarray(y_true, dtype=int).ravel()
    def nll(t_arr):
        T = max(1e-3, float(t_arr[0]))
        p = 1.0/(1.0 + np.exp(-logits/T))
        eps=1e-12
        return -np.mean(y_true*np.log(p+eps) + (1-y_true)*np.log(1-p+eps))
    # boundsあり最小化
    from math import inf
    try:
        return float(minimize(nll, x0=[1.0], bounds=[(1e-3, 100.0)]).x[0])
    except Exception:
        return 1.0

def _noise_injection(p: np.ndarray, level: float=0.05) -> np.ndarray:
    return np.clip(p + np.random.normal(0.0, level, size=p.shape), 0.0, 1.0)

def _time_shift(p: np.ndarray, k: int=1) -> np.ndarray:
    q = np.roll(p, k)
    q[:k] = float(np.median(p))
    return q

def _regime_flip(p: np.ndarray, strength: float=0.2) -> np.ndarray:
    drift = np.linspace(-strength, strength, num=p.shape[0])
    return np.clip(p + drift, 0.0, 1.0)

def _bin_acc(p: np.ndarray, y: np.ndarray, thr: float=0.5) -> float:
    return float(np.mean((p >= thr).astype(int) == y))

def _write_meta_probs_and_adv(reports_dir: Path, y_true, logits=None, y_prob=None, thr: float=0.5):
    \"\"\"meta.json に predicted_prob / labels / adv_results を追記（存在すればマージ）\"\"\"
    reports_dir.mkdir(parents=True, exist_ok=True)
    meta_path = reports_dir / "meta.json"
    import json
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    except Exception:
        meta = {}

    y_true = np.asarray(y_true, dtype=int).ravel()
    if logits is not None:
        logits = np.asarray(logits, dtype=float).ravel()
        T = _temperature_scale(logits, y_true)
        y_prob = 1.0/(1.0 + np.exp(-logits/max(1e-3, float(T))))
    elif y_prob is not None:
        y_prob = np.asarray(y_prob, dtype=float).ravel()
    else:
        return  # 何も無ければスキップ

    meta["labels"] = [int(v) for v in y_true.tolist()]
    meta["predicted_prob"] = [float(v) for v in y_prob.tolist()]

    # 逆境：3系統×各10ケース、通常精度の90%維持でpass
    base_acc = _bin_acc(y_prob, y_true, thr)
    target = 0.9 * base_acc
    passes = []
    for i in range(10):
        passes.append(_bin_acc(_noise_injection(y_prob, 0.05+0.01*i), y_true, thr) >= target)
    for k in range(1, 11):
        passes.append(_bin_acc(_time_shift(y_prob, k), y_true, thr) >= target)
    for i in range(10):
        passes.append(_bin_acc(_regime_flip(y_prob, 0.1+0.02*i), y_true, thr) >= target)
    meta["adv_results"] = [bool(x) for x in passes]

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
"""

AGG_INIT = """\
    # サンプル粒度の配列を集約（任意）
    agg_y_true: List[int] = []
    agg_y_prob: List[float] = []
    agg_logits: List[float] = []

    # レポ出力先（runごとにディレクトリ作成：UTC）
    run_dir = REPORTS_BASE / dt.datetime.now(dt.timezone.utc).strftime("run_%Y%m%dT%H%M%S")
"""

COLLECT_BLOCK = """\
            # optional フィールドを回収（あれば）
            try:
                if isinstance(result.get("y_true"), list):
                    agg_y_true.extend(int(v) for v in result["y_true"])
                if isinstance(result.get("y_prob"), list):
                    agg_y_prob.extend(float(v) for v in result["y_prob"])
                if isinstance(result.get("logits"), list):
                    agg_logits.extend(float(v) for v in result["logits"])
            except Exception:
                pass
"""

FINAL_META = """\
    # 可能なら meta.json 生成（確率/ラベルが1件以上集まった場合）
    try:
        if agg_logits:
            _write_meta_probs_and_adv(run_dir, agg_y_true, logits=np.array(agg_logits))
        elif agg_y_prob and agg_y_true and len(agg_y_prob) == len(agg_y_true):
            _write_meta_probs_and_adv(run_dir, agg_y_true, y_prob=np.array(agg_y_prob))
        else:
            logging.info("meta.json: y_prob/logits が無く、Prometheus KPI はスキップ（後方互換）。")
    except Exception as e:
        logging.warning(f"meta.json 生成に失敗: {e}")
"""

def insert_once(buf: str, marker_regex: str, insert_after: str) -> str:
    if re.search(re.escape(insert_after.strip()), buf):
        return buf  # already inserted
    m = re.search(marker_regex, buf, flags=re.S)
    if not m:
        return buf
    idx = m.end()
    return buf[:idx] + "\n" + insert_after + "\n" + buf[idx:]

def main() -> int:
    if not TARGET.exists():
        print(f"[patch] not found: {TARGET}", file=sys.stderr)
        return 2

    text = TARGET.read_text(encoding="utf-8")

    # 1) imports
    if "import numpy as np" not in text:
        # after existing import block
        text = re.sub(r"(^from pathlib import Path.*?\n)(from typing.*?\n)",
                      r"\1\2" + IMPORTS, text, flags=re.S|re.M)
        if "import numpy as np" not in text:
            # fallback: just prepend near the top
            text = text.replace("import pandas as pd\n", "import pandas as pd\n" + IMPORTS)

    # 2) helpers after TEST_DATA_PATH line
    if "REPORTS_BASE = Path(\"reports\") / \"veritas\"" not in text:
        text = insert_once(text, r"TEST_DATA_PATH\s*=\s*.*?\n", HELPERS)

    # 3) agg init inside main() after results declaration
    if "agg_y_true" not in text:
        text = re.sub(r"(results:\s*List\[Dict\[str,\s*Any\]\]\s*=\s*\[\]\s*\n)",
                      r"\1" + AGG_INIT, text)

    # 4) collect block after results.append(result) in the for loop
    if "optional フィールドを回収" not in text:
        text = text.replace("results.append(result)\n", "results.append(result)\n" + COLLECT_BLOCK)

    # 5) final meta block near end of main (after logging 語句のあと)
    if "meta.json 生成に失敗" not in text:
        text = text.replace(
            'logging.info("📜 訓示:『数の知恵を集めよ、勝利の礎となすべし』")\n',
            'logging.info("📜 訓示:『数の知恵を集めよ、勝利の礎となすべし』")\n\n' + FINAL_META
        )

    TARGET.write_text(text, encoding="utf-8")
    print("[patch] applied (idempotent).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
