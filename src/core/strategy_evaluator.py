# src/core/strategy_evaluator.py
#!/usr/bin/env python3
# coding: utf-8

"""
📊 Strategy Evaluator (Noctria) — unified v2.1

目的
- GUI → 一括DAG(veritas_recheck_all_dag) → 個別DAG(veritas_recheck_dag) から呼ばれる
  評価ロジックの**単一入口**。
- 返却スキーマを PDCA サマリー系に合わせて**標準化**する
  （winrate_old/new, maxdd_old/new, ...）。
- ログ保存は「日別CSV（PDCA集計向け）」＋「JSONアーカイブ（任意閲覧向け）」の
  **二重記録**を行う。

互換
- 以前の実装で使っていた `win_rate` / `max_drawdown` だけの形式も内部で標準化。
- 呼び出し元（DAG）から追加された `decision_id`, `caller`, `parent_dag`,
  `trigger_reason` 等はそのまま追記される。

出力スキーマ（最低限）
- strategy, evaluated_at,
- winrate_old, winrate_new,
- maxdd_old, maxdd_new,
- trades_old, trades_new,
- tag, notes,
- （必要に応じて）winrate_diff, maxdd_diff, decision_id, caller, parent_dag, trigger_reason, passed
"""

from __future__ import annotations

import csv
import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# --------------------------------------------------------------------------------------
# ルート・パス設定（path_config が無くても動くようにフォールバック）
# --------------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

try:
    # 絶対インポート前提（src/core/path_config.py）
    from src.core.path_config import (  # type: ignore
        STRATEGIES_DIR,                         # 例: <repo>/src/strategies
        STRATEGIES_VERITAS_GENERATED_DIR,       # 例: <repo>/src/strategies/veritas_generated
        ACT_LOG_DIR,                            # 例: <repo>/data/pdca_logs/veritas_orders とは別管理でもOK
        PDCA_LOG_DIR as _PDCA_LOG_DIR_SETTING,  # あれば使う
    )
except Exception:
    # フォールバック（代表的な配置を推定）
    STRATEGIES_DIR = SRC_DIR / "strategies"
    STRATEGIES_VERITAS_GENERATED_DIR = STRATEGIES_DIR / "veritas_generated"
    ACT_LOG_DIR = PROJECT_ROOT / "data" / "act_logs"
    _PDCA_LOG_DIR_SETTING = None  # 後でデフォルトに差し替え

# PDCA サマリが読む既定のログ置き場
PDCA_LOG_DIR = Path(_PDCA_LOG_DIR_SETTING) if _PDCA_LOG_DIR_SETTING else (PROJECT_ROOT / "data" / "pdca_logs" / "veritas_orders")
PDCA_LOG_DIR.mkdir(parents=True, exist_ok=True)
ACT_LOG_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------------
# ロガー
# --------------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("StrategyEvaluator")

# --------------------------------------------------------------------------------------
# 王国の採用基準（必要に応じて .env / path_config へ移す）
# --------------------------------------------------------------------------------------
WIN_RATE_THRESHOLD = 60.0       # 最低勝率（%）
MAX_DRAWDOWN_THRESHOLD = 20.0   # 最大許容ドローダウン（%）

# --------------------------------------------------------------------------------------
# ユーティリティ
# --------------------------------------------------------------------------------------
_STD_KEYS = [
    "strategy", "evaluated_at",
    "winrate_old", "winrate_new",
    "maxdd_old", "maxdd_new",
    "trades_old", "trades_new",
    "tag", "notes",
]

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _coerce_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _strategy_file_candidates(strategy_name: str) -> list[Path]:
    """
    戦略ファイルの可能性がある場所を列挙（存在チェックは呼び出し側で）。
    - veritas_generated/{name}.py を優先
    - strategies/{name}.py も候補
    """
    return [
        STRATEGIES_VERITAS_GENERATED_DIR / f"{strategy_name}.py",
        STRATEGIES_DIR / f"{strategy_name}.py",
    ]

def _ensure_standard_result(strategy_name: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    dict を標準キーに整形する。
    - 以前の v2.0（win_rate/max_drawdown）も吸収。
    """
    # 旧キーの吸収
    win_new = raw.get("winrate_new")
    if win_new is None:
        win_new = raw.get("win_rate")

    dd_new = raw.get("maxdd_new")
    if dd_new is None:
        dd_new = raw.get("max_drawdown")

    res: Dict[str, Any] = {
        "strategy": strategy_name,
        "evaluated_at": raw.get("evaluated_at") or raw.get("timestamp") or _utc_now_iso(),
        "winrate_old": _coerce_float(raw.get("winrate_old")),
        "winrate_new": _coerce_float(win_new),
        "maxdd_old": _coerce_float(raw.get("maxdd_old")),
        "maxdd_new": _coerce_float(dd_new),
        "trades_old": _coerce_float(raw.get("trades_old")),
        "trades_new": _coerce_float(raw.get("trades_new")),
        "tag": raw.get("tag") or "recheck",
        "notes": raw.get("notes") or "",
    }
    # diff の計算
    if res["winrate_old"] is not None and res["winrate_new"] is not None:
        res["winrate_diff"] = round(res["winrate_new"] - res["winrate_old"], 6)
    if res["maxdd_old"] is not None and res["maxdd_new"] is not None:
        res["maxdd_diff"] = round(res["maxdd_new"] - res["maxdd_old"], 6)

    # 追加キーは温存（decision_id, caller, parent_dag, trigger_reason, passed 等）
    for k, v in raw.items():
        if k not in res:
            res[k] = v
    return res

def is_strategy_adopted(evaluation_result: Dict[str, Any]) -> bool:
    """
    採用基準: 勝率 >= WIN_RATE_THRESHOLD かつ DD <= MAX_DRAWDOWN_THRESHOLD
    - v2.0 の win_rate/max_drawdown だけがある場合でも _ensure_standard_result 前提で呼ぶため OK。
    """
    wr = evaluation_result.get("winrate_new")
    dd = evaluation_result.get("maxdd_new")
    try:
        wr_f = float(wr) if wr is not None else -1e9
        dd_f = float(dd) if dd is not None else 1e9
    except Exception:
        wr_f, dd_f = -1e9, 1e9

    ok = (wr_f >= WIN_RATE_THRESHOLD) and (dd_f <= MAX_DRAWDOWN_THRESHOLD)
    logger.info("採用判定: strategy=%s -> %s (win=%.2f%%, dd=%.2f%%)", evaluation_result.get("strategy"), "PASS" if ok else "FAIL", wr_f, dd_f)
    return ok

# --------------------------------------------------------------------------------------
# 評価本体
# --------------------------------------------------------------------------------------
def evaluate_strategy(strategy_name: str) -> Dict[str, Any]:
    """
    指定戦略を評価して標準スキーマで返す。
    - ここではダミーのスコア生成（seed は strategy_name 由来で準再現性）
    - 実運用ではバックテスト or 推論実行ロジックに差し替える
    """
    # 戦略ファイル存在チェック（最低限）
    candidates = _strategy_file_candidates(strategy_name)
    if not any(p.exists() for p in candidates):
        msg = f"Strategy file not found for '{strategy_name}'. Searched: " + ", ".join(str(p) for p in candidates)
        logger.error(msg)
        raise FileNotFoundError(msg)

    # ダミー評価（準再現性）
    seed_value = sum(ord(c) for c in strategy_name)
    random.seed(seed_value)
    win_rate = round(random.uniform(50.0, 75.0), 2)     # 50〜75%
    max_dd = round(random.uniform(5.0, 30.0), 2)        # 5〜30%
    trades = int(random.uniform(20, 200))               # 20〜200

    raw = {
        "strategy": strategy_name,
        "evaluated_at": _utc_now_iso(),
        "winrate_old": None,
        "winrate_new": win_rate,
        "maxdd_old": None,
        "maxdd_new": max_dd,
        "trades_old": None,
        "trades_new": trades,
        "tag": "recheck",
        "notes": "dummy evaluation (replace with real backtest)",
    }

    result = _ensure_standard_result(strategy_name, raw)
    result["passed"] = is_strategy_adopted(result)
    return result

# --------------------------------------------------------------------------------------
# ロギング
# --------------------------------------------------------------------------------------
def _pdca_csv_headers(extra_keys: list[str]) -> list[str]:
    base = [
        "strategy", "evaluated_at",
        "winrate_old", "winrate_new",
        "maxdd_old", "maxdd_new",
        "trades_old", "trades_new",
        "tag", "notes",
        "winrate_diff", "maxdd_diff",
        "trigger_reason", "decision_id", "caller", "parent_dag",
        "passed",
    ]
    # 衝突しない追加キーを末尾に
    for k in extra_keys:
        if k not in base:
            base.append(k)
    return base

def log_evaluation_result(evaluation_result: Dict[str, Any]) -> None:
    """
    評価結果の保存：
    1) PDCA向け 日別CSV: data/pdca_logs/veritas_orders/rechecks_YYYY-MM-DD.csv
    2) JSONアーカイブ   : ACT_LOG_DIR/eval_{strategy}_{YYYYmmdd_HHMMSS}.json
    """
    # --- 1) PDCA CSV 追記 ---
    date_part = str(evaluation_result.get("evaluated_at", _utc_now_iso()))[:10]  # YYYY-MM-DD
    csv_path = PDCA_LOG_DIR / f"rechecks_{date_part}.csv"

    # 動的キー（標準キー以外）
    dynamic_keys = [k for k in evaluation_result.keys() if k not in _STD_KEYS + ["winrate_diff", "maxdd_diff"]]
    headers = _pdca_csv_headers(sorted(dynamic_keys))

    write_header = not csv_path.exists()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        if write_header:
            w.writeheader()
        row = {h: evaluation_result.get(h) for h in headers}
        w.writerow(row)
    logger.info("PDCA CSV appended: %s", csv_path)

    # --- 2) JSON アーカイブ ---
    strategy_id = evaluation_result.get("strategy") or "unknown_strategy"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = ACT_LOG_DIR / f"eval_{strategy_id}_{ts}.json"
    try:
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(evaluation_result, f, ensure_ascii=False, indent=2)
        logger.info("Archive JSON saved: %s", json_path)
    except Exception as e:
        logger.warning("Archive JSON save failed: %s", e)

# --------------------------------------------------------------------------------------
# 単体実行
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("--- 戦略評価モジュールの単体テストを開始 ---")
    dummy_strategy = "veritas_test_strategy_001"

    # ダミー戦略ファイル（存在チェックに通すための空ファイル）
    dummy_path = STRATEGIES_VERITAS_GENERATED_DIR / f"{dummy_strategy}.py"
    dummy_path.parent.mkdir(parents=True, exist_ok=True)
    if not dummy_path.exists():
        dummy_path.write_text("# dummy strategy for local test\n")

    try:
        result = evaluate_strategy(dummy_strategy)
        print("\n[評価結果]:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        log_evaluation_result(result)
    finally:
        # 片付け（コメントアウトで残しても可）
        try:
            dummy_path.unlink()
        except Exception:
            pass
    logger.info("--- 戦略評価モジュールの単体テストを完了 ---")
