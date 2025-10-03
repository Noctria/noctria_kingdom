#!/usr/bin/env python3
# coding: utf-8

"""
⚖️ Veritas Machina Evaluator (ML専用)
- Veritasが生成した全ML戦略を評価し、合格戦略をJSONに集約
- Airflow等のワークフローからも直接呼び出し可能
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ===== Robust import bootstrap =====
try:
    from src.core.path_config import (
        DATA_DIR,
        STRATEGIES_VERITAS_GENERATED_DIR,
        VERITAS_EVAL_LOG,
    )
except Exception:
    this_file = Path(__file__).resolve()
    project_root = this_file.parents[2]
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    try:
        from core.path_config import (
            DATA_DIR,
            STRATEGIES_VERITAS_GENERATED_DIR,
            VERITAS_EVAL_LOG,
        )
    except Exception as e:
        raise ImportError(
            f"path_config の読み込みに失敗しました。"
            f"PYTHONPATH に {project_root} を追加するか、`python -m` でパッケージ実行してください。"
        ) from e

# ロガー設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

# --- 戦略採用基準（ML的な数値重視） ---
WIN_RATE_THRESHOLD = 0.50
MAX_DRAWDOWN_THRESHOLD = 0.30
MIN_TRADES_THRESHOLD = 10

TEST_DATA_PATH = DATA_DIR / "sample_test_data.csv"
REPORTS_BASE = Path("reports") / "veritas"

# ---- optional helpers (temperature scaling & adversarial) ----
try:
    from scipy.optimize import minimize  # type: ignore
except Exception:
    minimize = None

# ===== Global flags (CLIで上書き) =====
CALIBRATE_T: bool = True


def _safe_clip(p: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    return np.clip(p, eps, 1.0 - eps)


def _logit(p: np.ndarray) -> np.ndarray:
    p = _safe_clip(p)
    return np.log(p) - np.log(1 - p)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _apply_temperature_probs(y_prob: np.ndarray, T: float) -> np.ndarray:
    logits = _logit(y_prob)
    scaled = logits / max(T, 1e-6)
    return _safe_clip(_sigmoid(scaled))


def _nll_binary(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    p = _safe_clip(y_prob)
    return float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))


def _ece_binary(y_prob: np.ndarray, y_true: np.ndarray, bins: int = 10) -> float:
    y_prob = np.asarray(y_prob, dtype=float).ravel()
    y_true = np.asarray(y_true, dtype=int).ravel()
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    N = len(y_prob)
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        m = (y_prob >= lo) & (y_prob < hi if i < bins - 1 else y_prob <= hi)
        if not np.any(m):
            continue
        conf = float(np.mean(y_prob[m]))
        acc = float(np.mean((y_prob[m] >= 0.5).astype(int) == y_true[m]))
        ece += (np.sum(m) / N) * abs(acc - conf)
    return float(ece)


def _estimate_temperature_probs(
    y_true: np.ndarray, y_prob: np.ndarray, max_T: float = 10.0
) -> Tuple[float, float, np.ndarray]:
    """
    確率のみ→ロジット→温度粗探索（依存ゼロ）
    返り値: (T_best, best_nll, y_prob_scaled)
    """
    candidates = np.unique(
        np.concatenate(
            [
                np.linspace(0.05, 0.5, 10),
                np.linspace(0.6, min(3.0, max_T), 25),
                np.linspace(min(3.5, max_T * 0.35), max_T, 14),
            ]
        )
    )
    best_T, best_loss = 1.0, _nll_binary(y_true, y_prob)
    best_prob = y_prob
    for T in candidates:
        T = float(np.clip(T, 1e-3, max_T))
        pr = _apply_temperature_probs(y_prob, T)
        loss = _nll_binary(y_true, pr)
        if loss < best_loss:
            best_T, best_loss, best_prob = T, loss, pr
    return float(best_T), float(best_loss), best_prob


def _temperature_scale_logits(
    logits: np.ndarray, y_true: np.ndarray, max_T: float = 10.0
) -> Tuple[float, float, np.ndarray]:
    """
    ロジット→scipy最適化（無ければ T=1.0）
    返り値: (T_best, best_nll, y_prob_scaled)
    """
    logits = np.asarray(logits, dtype=float).ravel()
    y_true = np.asarray(y_true, dtype=int).ravel()
    if minimize is None:
        pr = _safe_clip(_sigmoid(logits))
        return 1.0, _nll_binary(y_true, pr), pr

    def nll(t_arr):
        T = float(np.clip(t_arr[0], 1e-3, max_T))
        p = _safe_clip(_sigmoid(logits / T))
        return _nll_binary(y_true, p)

    try:
        res = minimize(nll, x0=[1.0], bounds=[(1e-3, max_T)])
        T = float(np.clip(res.x[0], 1e-3, max_T))
        pr = _safe_clip(_sigmoid(logits / T))
        return T, _nll_binary(y_true, pr), pr
    except Exception:
        pr = _safe_clip(_sigmoid(logits))
        return 1.0, _nll_binary(y_true, pr), pr


def _noise_injection(p: np.ndarray, level: float = 0.05) -> np.ndarray:
    return np.clip(p + np.random.normal(0.0, level, size=p.shape), 0.0, 1.0)


def _time_shift(p: np.ndarray, k: int = 1) -> np.ndarray:
    q = np.roll(p, k)
    q[:k] = float(np.median(p))
    return q


def _regime_flip(p: np.ndarray, strength: float = 0.2) -> np.ndarray:
    drift = np.linspace(-strength, strength, num=p.shape[0])
    return np.clip(p + drift, 0.0, 1.0)


def _bin_acc(p: np.ndarray, y: np.ndarray, thr: float = 0.5) -> float:
    return float(np.mean((p >= thr).astype(int) == y))


# ---- prior-T（直近runの温度）拾い上げ ----
def _latest_calib_T() -> Optional[float]:
    try:
        metas = sorted(
            REPORTS_BASE.glob("run_*/meta.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        for m in metas:
            data = json.loads(m.read_text(encoding="utf-8"))
            if isinstance(data, list):
                data = data[-1] if data and isinstance(data[-1], dict) else {}
            T = (data.get("calibration") or {}).get("temperature")
            if isinstance(T, (int, float)) and T > 0:
                return float(T)
    except Exception:
        pass
    return None


# ---- fallback generators ----
def _labels_from_price(df: pd.DataFrame) -> Optional[np.ndarray]:
    if "price" not in df.columns:
        return None
    y = (df["price"].shift(-1) > df["price"]).astype(float).values[:-1]
    return y.astype(int)


def _probs_from_rsi(df: pd.DataFrame) -> Optional[np.ndarray]:
    col = "RSI(14)"
    if col not in df.columns:
        return None
    x = (df[col].values[:-1] - 50.0) / 8.0
    return 1.0 / (1.0 + np.exp(-x))


def _calibrate_with_guardrails(
    y_true: np.ndarray,
    base_prob: np.ndarray,
    used_logits: Optional[np.ndarray],
    objective: str,
    bins: int,
    max_T: float,
    prior_T: Optional[float],
    guard_nll_deg: float,
    guard_ece_improve_min: float,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    NLL/ECEの両案を試し、ガードレールを満たす方を採用。
    """
    y_true = np.asarray(y_true, int).ravel()
    base_prob = _safe_clip(np.asarray(base_prob, float).ravel())
    prior_T = float(prior_T) if isinstance(prior_T, (int, float)) and prior_T > 0 else None

    # before metrics
    before_nll = _nll_binary(y_true, base_prob)
    before_ece = _ece_binary(base_prob, y_true, bins=bins)

    # ---- NLL-opt
    if used_logits is not None:
        T_nll, nll_after_nll, prob_nll = _temperature_scale_logits(used_logits, y_true, max_T=max_T)
    else:
        T_nll, nll_after_nll, prob_nll = _estimate_temperature_probs(y_true, base_prob, max_T=max_T)
    ece_after_nll = _ece_binary(prob_nll, y_true, bins=bins)

    # ---- ECE-opt（粗探索）
    # 探索グリッドは NLLと同等に max_T まで。ただし ECE最小のTを選ぶ。
    candidates = np.unique(
        np.concatenate(
            [
                np.linspace(0.05, 0.5, 10),
                np.linspace(0.6, min(3.0, max_T), 25),
                np.linspace(min(3.5, max_T * 0.35), max_T, 14),
            ]
        )
    )
    best_T_ece = 1.0
    best_prob_ece = base_prob
    best_ece = before_ece
    for T in candidates:
        pr = _apply_temperature_probs(base_prob, float(np.clip(T, 1e-3, max_T)))
        e = _ece_binary(pr, y_true, bins=bins)
        if e < best_ece:
            best_ece, best_T_ece, best_prob_ece = e, float(T), pr
    T_ece, prob_ece = best_T_ece, best_prob_ece
    nll_after_ece = _nll_binary(y_true, prob_ece)
    ece_after_ece = best_ece

    # ---- prior_T（あれば）評価
    prob_prior = None
    nll_after_prior = None
    ece_after_prior = None
    if prior_T is not None:
        if used_logits is not None:
            prob_prior = _safe_clip(_sigmoid(used_logits / max(prior_T, 1e-6)))
        else:
            prob_prior = _apply_temperature_probs(base_prob, prior_T)
        nll_after_prior = _nll_binary(y_true, prob_prior)
        ece_after_prior = _ece_binary(prob_prior, y_true, bins=bins)

    # ---- 選択ポリシ（objective）
    chosen = "nll"
    y_prob_final = prob_nll
    T_final = T_nll

    if objective == "nll":
        chosen = "nll"
        y_prob_final, T_final = prob_nll, T_nll
    elif objective == "ece":
        # ECEの改善が guard_ece_improve_min 以上、かつ NLL悪化が guard_nll_deg 以下なら eceを採用
        nll_worse_ratio = (nll_after_ece - before_nll) / max(before_nll, 1e-9)
        ece_gain = before_ece - ece_after_ece
        if (ece_gain >= guard_ece_improve_min) and (nll_worse_ratio <= guard_nll_deg):
            chosen = "ece"
            y_prob_final, T_final = prob_ece, T_ece
        else:
            chosen = "nll"
            y_prob_final, T_final = prob_nll, T_nll
    else:  # both
        # まず NLL-opt を基準、ECE-opt はガードを満たす場合のみ候補に。
        nll_worse_ratio = (nll_after_ece - before_nll) / max(before_nll, 1e-9)
        ece_gain = before_ece - ece_after_ece
        use_ece = (ece_gain >= guard_ece_improve_min) and (nll_worse_ratio <= guard_nll_deg)

        cand = [("nll", prob_nll, T_nll, nll_after_nll, ece_after_nll)]
        if use_ece:
            cand.append(("ece", prob_ece, T_ece, nll_after_ece, ece_after_ece))
        if (
            (prob_prior is not None)
            and (nll_after_prior is not None)
            and (ece_after_prior is not None)
        ):
            cand.append(("prior", prob_prior, float(prior_T), nll_after_prior, ece_after_prior))

        # 2目的の単純化：まず NLL を優先、同等なら ECE が良い方
        cand.sort(key=lambda x: (x[3], x[4]))
        chosen, y_prob_final, T_final, _, _ = cand[0]

    meta = {
        "applied": True,
        "objective": objective,
        "prior_T": prior_T,
        "chosen": chosen,
        "T_nll": float(T_nll),
        "T_ece": float(T_ece),
        "temperature": float(T_final),
        "before_nll": round(float(before_nll), 6),
        "before_ece": round(float(before_ece), 6),
        "after_nll_by_nll": round(float(nll_after_nll), 6),
        "after_ece_by_nll": round(float(ece_after_nll), 6),
        "after_nll_by_ece": round(float(nll_after_ece), 6),
        "after_ece_by_ece": round(float(ece_after_ece), 6),
        "method": "binary_temperature_scaling_logits"
        if used_logits is not None
        else "binary_temperature_scaling_probs",
        "used_prior": bool(chosen == "prior"),
        "bins": int(bins),
        "guard_nll_deg": float(guard_nll_deg),
        "guard_ece_improve_min": float(guard_ece_improve_min),
    }
    return y_prob_final, meta


def _write_meta_probs_and_adv(
    reports_dir: Path,
    y_true,
    logits=None,
    y_prob=None,
    *,
    thr: float = 0.5,
    calib_objective: str = "both",
    calib_bins: int = 10,
    calib_max_T: float = 10.0,
    guard_nll_deg: float = 0.05,
    guard_ece_improve_min: float = 0.02,
    adv_keep: float = 0.90,
):
    """meta.json に predicted_prob / labels / adv_results / calibration / run_id を追記"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    meta_path = reports_dir / "meta.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    except Exception:
        meta = {}

    meta["run_id"] = reports_dir.name

    y_true = np.asarray(y_true, dtype=int).ravel()
    used_logits = None
    if logits is not None:
        used_logits = np.asarray(logits, dtype=float).ravel()
        y_prob0 = _safe_clip(_sigmoid(used_logits))
    elif y_prob is not None:
        y_prob0 = _safe_clip(np.asarray(y_prob, dtype=float).ravel())
    else:
        return

    # 温度スケーリング with guardrails
    if CALIBRATE_T and len(y_true) == len(y_prob0) and len(y_true) > 8:
        prior_T = _latest_calib_T()
        y_prob_final, calib_meta = _calibrate_with_guardrails(
            y_true=y_true,
            base_prob=y_prob0,
            used_logits=used_logits,
            objective=calib_objective,
            bins=calib_bins,
            max_T=calib_max_T,
            prior_T=prior_T,
            guard_nll_deg=guard_nll_deg,
            guard_ece_improve_min=guard_ece_improve_min,
        )
    else:
        y_prob_final = y_prob0
        calib_meta = {
            "applied": False,
            "reason": "disabled_or_insufficient_data",
            "objective": calib_objective,
            "bins": calib_bins,
        }

    # 書き込み
    meta["labels"] = [int(v) for v in y_true.tolist()]
    meta["predicted_prob"] = [float(v) for v in y_prob_final.tolist()]
    meta["calibration"] = calib_meta

    # 逆境：3系統×各10ケース、通常精度の adv_keep でパス
    base_acc = _bin_acc(y_prob_final, y_true, thr)
    target = float(adv_keep) * base_acc
    passes: List[bool] = []
    for i in range(10):
        passes.append(
            _bin_acc(_noise_injection(y_prob_final, 0.05 + 0.01 * i), y_true, thr) >= target
        )
    for k in range(1, 11):
        passes.append(_bin_acc(_time_shift(y_prob_final, k), y_true, thr) >= target)
    for i in range(10):
        passes.append(_bin_acc(_regime_flip(y_prob_final, 0.1 + 0.02 * i), y_true, thr) >= target)
    meta["adv_results"] = [bool(x) for x in passes]

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_strategy_module(strategy_path: Path) -> Optional[Any]:
    try:
        module_name = f"strategies.veritas_generated.{strategy_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, strategy_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"モジュール仕様の取得失敗: {strategy_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logging.error(f"戦略モジュール読み込み失敗: {strategy_path}, エラー: {e}", exc_info=True)
        return None


def _extract_probs_from_strategy(strategy_module: Any, test_data: pd.DataFrame):
    probs = None
    try:
        if hasattr(strategy_module, "predict_proba"):
            probs = np.asarray(strategy_module.predict_proba(test_data), dtype=float).ravel()
        elif hasattr(strategy_module, "predict"):
            scores = np.asarray(strategy_module.predict(test_data), dtype=float).ravel()
            probs = 1.0 / (1.0 + np.exp(-scores))
    except Exception:
        probs = None

    if probs is None or len(probs) == 0:
        return None, None

    if "price" in test_data.columns:
        y_true = (test_data["price"].shift(-1) > test_data["price"]).astype(int).to_numpy()
        y_true = y_true[: len(probs)]
        probs = probs[: len(y_true)]
        return probs, y_true
    return probs, None


def _is_strategy_adopted(result: Dict[str, Any]) -> bool:
    return (
        result.get("final_capital", 0) > 1_000_000
        and result.get("win_rate", 0.0) >= WIN_RATE_THRESHOLD
        and result.get("max_drawdown", 1.0) <= MAX_DRAWDOWN_THRESHOLD
        and result.get("total_trades", 0) >= MIN_TRADES_THRESHOLD
    )


def _evaluate_single_strategy(strategy_path: Path, test_data: pd.DataFrame) -> Dict[str, Any]:
    strategy_module = _load_strategy_module(strategy_path)
    if strategy_module is None:
        return {"strategy": strategy_path.name, "error": "モジュール読み込み失敗", "passed": False}
    if not hasattr(strategy_module, "simulate"):
        return {
            "strategy": strategy_path.name,
            "error": "simulate関数が存在しません。",
            "passed": False,
        }
    try:
        result = strategy_module.simulate(test_data)
        if not isinstance(result, dict):
            raise TypeError("simulateの戻り値がdictではありません。")
        result["strategy"] = strategy_path.name
        result["passed"] = _is_strategy_adopted(result)
        return result
    except Exception as e:
        logging.error(f"戦略『{strategy_path.name}』評価エラー: {e}", exc_info=True)
        return {"strategy": strategy_path.name, "error": str(e), "passed": False}


def _load_test_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required_cols = {"RSI(14)", "spread", "price"}
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        logging.warning(f"評価データに想定列がありません: {missing} / 既存列: {list(df.columns)}")
    return df


def main():
    global CALIBRATE_T

    parser = argparse.ArgumentParser()
    parser.add_argument("--calibrate-temperature", dest="calib", action="store_true", default=True)
    parser.add_argument("--no-calibrate-temperature", dest="calib", action="store_false")
    parser.add_argument("--calib-objective", choices=["nll", "ece", "both"], default="both")
    parser.add_argument("--calib-bins", type=int, default=10)
    parser.add_argument("--calib-max-T", type=float, default=10.0)
    parser.add_argument(
        "--guard-nll-deg", type=float, default=0.05, help="NLL許容悪化率（例: 0.05=+5%まで）"
    )
    parser.add_argument("--guard-ece-improve-min", type=float, default=0.02, help="ECEの最小改善幅")
    parser.add_argument(
        "--adv-keep", type=float, default=0.90, help="逆境時に維持すべき通常精度比 (0~1)"
    )
    args, _ = parser.parse_known_args()

    CALIBRATE_T = bool(args.calib)

    logging.info("⚖️ [Veritas Machina] 全戦略の評価を開始します…")
    if not TEST_DATA_PATH.exists():
        logging.error(f"評価用データが見つかりません: {TEST_DATA_PATH}")
        raise FileNotFoundError(f"Test data not found: {TEST_DATA_PATH}")

    test_data = _load_test_data(TEST_DATA_PATH)
    results: List[Dict[str, Any]] = []

    agg_y_true: List[int] = []
    agg_y_prob: List[float] = []
    agg_logits: List[float] = []

    run_dir = REPORTS_BASE / dt.datetime.now(dt.timezone.utc).strftime("run_%Y%m%dT%H%M%S")

    if not STRATEGIES_VERITAS_GENERATED_DIR.exists():
        logging.warning(f"戦略ディレクトリが存在しません: {STRATEGIES_VERITAS_GENERATED_DIR}")
    else:
        strategy_files = sorted(STRATEGIES_VERITAS_GENERATED_DIR.glob("*.py"))
        logging.info(f"{len(strategy_files)}件の戦略を発見。")
        for path in strategy_files:
            result = _evaluate_single_strategy(path, test_data)
            results.append(result)

            try:
                if isinstance(result.get("y_true"), list):
                    agg_y_true.extend(int(v) for v in result["y_true"])
                if isinstance(result.get("y_prob"), list):
                    agg_y_prob.extend(float(v) for v in result["y_prob"])
                if isinstance(result.get("logits"), list):
                    agg_logits.extend(float(v) for v in result["logits"])
            except Exception:
                pass

            try:
                need_prob = (len(agg_logits) == 0) and (len(agg_y_prob) == 0)
                if need_prob:
                    sm = _load_strategy_module(path)
                    if sm is not None:
                        p, y = _extract_probs_from_strategy(sm, test_data)
                        if p is not None:
                            result.setdefault("y_prob", []).extend([float(v) for v in p.tolist()])
                            agg_y_prob.extend([float(v) for v in p.tolist()])
                            if y is not None:
                                result.setdefault("y_true", []).extend([int(v) for v in y.tolist()])
                                agg_y_true.extend([int(v) for v in y.tolist()])
            except Exception:
                pass

    # 評価結果ログ保存
    try:
        VERITAS_EVAL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(VERITAS_EVAL_LOG, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logging.error(f"評価ログ書き込み失敗: {VERITAS_EVAL_LOG}, エラー: {e}")

    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    logging.info(f"🧠 評価完了: {total}件の戦略を審査、合格: {passed_count}件")
    logging.info("📜 訓示:『数の知恵を集めよ、勝利の礎となすべし』")

    # meta.json 生成
    try:
        if agg_logits:
            _write_meta_probs_and_adv(
                run_dir,
                agg_y_true,
                logits=np.array(agg_logits),
                calib_objective=args.calib_objective,
                calib_bins=int(args.calib_bins),
                calib_max_T=float(args.calib_max_T),
                guard_nll_deg=float(args.guard_nll_deg),
                guard_ece_improve_min=float(args.guard_ece_improve_min),
                adv_keep=float(args.adv_keep),
            )
        elif agg_y_prob and agg_y_true and len(agg_y_prob) == len(agg_y_true):
            _write_meta_probs_and_adv(
                run_dir,
                agg_y_true,
                y_prob=np.array(agg_y_prob),
                calib_objective=args.calib_objective,
                calib_bins=int(args.calib_bins),
                calib_max_T=float(args.calib_max_T),
                guard_nll_deg=float(args.guard_nll_deg),
                guard_ece_improve_min=float(args.guard_ece_improve_min),
                adv_keep=float(args.adv_keep),
            )
        else:
            y = _labels_from_price(test_data)
            p = _probs_from_rsi(test_data)
            if y is not None and p is not None and len(y) == len(p) and len(y) >= 20:
                _write_meta_probs_and_adv(
                    run_dir,
                    y_true=y,
                    y_prob=p,
                    calib_objective=args.calib_objective,
                    calib_bins=int(args.calib_bins),
                    calib_max_T=float(args.calib_max_T),
                    guard_nll_deg=float(args.guard_nll_deg),
                    guard_ece_improve_min=float(args.guard_ece_improve_min),
                    adv_keep=float(args.adv_keep),
                )
                logging.info(
                    "meta.json: fallback(y_prob from RSI, labels from price) を出力しました。"
                )
            else:
                logging.info(
                    "meta.json: y_prob/logits が無く、Prometheus KPI はスキップ（後方互換）。"
                )
    except Exception as e:
        logging.warning(f"meta.json 生成に失敗: {e}")


if __name__ == "__main__":
    main()
