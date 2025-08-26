#!/usr/bin/env python3
# coding: utf-8
"""
Adapter→Decision CLI
- Strategy を読み込み、Feature を収集し、adapter→decision を実行して結果を表示
- 重要: path_config.ensure_import_path() で import 経路を安定化
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import traceback
from typing import Any, Optional, Tuple

# === 公式の import 経路ブートストラップ（最優先で実行） ===
from src.core.path_config import ensure_import_path, ensure_strategy_packages
ensure_import_path()          # repo ルート & src を sys.path に追加
ensure_strategy_packages()    # strategies/** の __init__.py を用意（無ければ自動作成）

# --- 以降はトップレベル import で統一 ---
from plan_data.collector import PlanDataCollector
from plan_data.strategy_adapter import FeatureBundle
from plan_data.adapter_to_decision import run_strategy_and_decide


def _load_strategy(target: str) -> Any:
    """
    "pkg.mod:ClassName" または "pkg.mod"（モジュールに DEFAULT_CLASS がある場合）をロード
    """
    if ":" in target:
        mod_name, cls_name = target.split(":", 1)
    else:
        mod_name, cls_name = target, None

    mod = importlib.import_module(mod_name)
    if cls_name:
        cls = getattr(mod, cls_name)
        return cls()  # デフォルトコンストラクタ想定
    if hasattr(mod, "DEFAULT_CLASS"):
        return getattr(mod, "DEFAULT_CLASS")()
    raise ValueError(f"Strategy class not specified and DEFAULT_CLASS not found in {mod_name}")


def _collect_features(symbol: str, timeframe: str, lookback: int) -> Tuple[Any, str]:
    """
    Collector を使って features の生素材（DataFrame）を収集
    戻り値は (df, trace_id)
    """
    collector = PlanDataCollector()
    df, tid = collector.collect_all(lookback_days=lookback)
    tid = df.attrs.get("trace_id", tid)
    return df, str(tid)


def _build_feature_bundle(
    df,
    trace_id: str,
    *,
    symbol: str,
    timeframe: str,
    trend: Optional[float],
    volatility: Optional[float],
    missing_ratio: Optional[float],
    data_lag_min: Optional[int],
) -> FeatureBundle:
    context = {
        "trace_id": trace_id,
        "symbol": symbol,
        "timeframe": timeframe,
    }
    if trend is not None:
        context["trend_score"] = float(trend)
    if volatility is not None:
        context["volatility"] = float(volatility)
    if missing_ratio is not None:
        context["missing_ratio"] = float(missing_ratio)
    if data_lag_min is not None:
        context["data_lag_min"] = int(data_lag_min)

    return FeatureBundle(df=df, context=context)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Run Strategy -> Adapter -> Decision (Plan layer CLI)")
    p.add_argument("--strategy", required=True, help='Strategy spec: "pkg.module:ClassName"')
    p.add_argument("--symbol", default="USDJPY")
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--lookback", type=int, default=90)

    # Decision ヒント上書き（任意）
    p.add_argument("--trend", type=float, default=None, help="Override trend_score (0..1)")
    p.add_argument("--volatility", type=float, default=None, help="Override volatility (>=0)")
    # Quality Gate 用の疑似悪化入力（任意）
    p.add_argument("--missing-ratio", type=float, default=None, help="Simulate missing_ratio (0..1)")
    p.add_argument("--data-lag-min", type=int, default=None, help="Simulate data_lag_min (minutes)")

    # 表示
    p.add_argument("--pretty", action="store_true", help="Pretty print JSON")

    # 観測 DB の明示 DSN（通常は環境変数 NOCTRIA_OBS_PG_DSN を利用）
    p.add_argument("--conn-dsn", default=None, help="PostgreSQL DSN for observability (optional)")

    args = p.parse_args(argv)

    try:
        # 1) Strategy ロード
        strategy = _load_strategy(args.strategy)

        # 2) データ収集
        df, tid = _collect_features(args.symbol, args.timeframe, args.lookback)

        # 3) FeatureBundle 構築
        fb = _build_feature_bundle(
            df,
            tid,
            symbol=args.symbol,
            timeframe=args.timeframe,
            trend=args.trend,
            volatility=args.volatility,
            missing_ratio=args.missing_ratio,
            data_lag_min=args.data_lag_min,
        )

        # 4) アダプタ→ディシジョン実行
        result = run_strategy_and_decide(
            strategy,
            fb,
            model_name=None,
            model_version=None,
            timeout_sec=None,
            conn_str=args.conn_dsn,
        )

        # 5) 出力
        if args.pretty:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(result, ensure_ascii=False))

        return 0

    except Exception as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
