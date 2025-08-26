# src/plan_data/adapter_to_decision_cli.py
from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any, Dict, Optional

# ---- まず import 経路を安定化（失敗しても続行）----
try:
    from src.core.path_config import ensure_import_path  # type: ignore
    ensure_import_path()
except Exception:
    pass

# ---- 明示的に src.* で統一（plan_data/decision を混在させない）----
from src.plan_data.collector import PlanDataCollector  # type: ignore
from src.plan_data.strategy_adapter import FeatureBundle  # type: ignore
from src.plan_data.adapter_to_decision import run_strategy_and_decide  # type: ignore


def _import_strategy(dotted: str):
    """
    例: "src.strategies.aurus_singularis:Aurus_Singularis"
        "src.strategies.levia_tempest:Levia_Tempest"
    """
    if ":" not in dotted:
        raise ValueError(f"strategy format must be 'module:ClassName', got: {dotted}")
    mod_name, cls_name = dotted.split(":", 1)
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    return cls


def build_features(symbol: str, timeframe: str, lookback: int,
                   override_missing_ratio: Optional[float],
                   override_data_lag_min: Optional[int],
                   extra_ctx: Dict[str, Any]) -> FeatureBundle:
    collector = PlanDataCollector()
    df, tid = collector.collect_all(lookback_days=max(lookback, 1))
    # 最低限の context
    ctx: Dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "trace_id": tid,
    }
    if override_missing_ratio is not None:
        ctx["missing_ratio"] = float(override_missing_ratio)
    if override_data_lag_min is not None:
        ctx["data_lag_min"] = int(override_data_lag_min)
    ctx.update(extra_ctx or {})
    return FeatureBundle(df=df, context=ctx)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Run strategy via adapter → DecisionEngine")
    p.add_argument("--strategy", required=True, help="module:Class (e.g. src.strategies.aurus_singularis:Aurus_Singularis)")
    p.add_argument("--symbol", default="USDJPY")
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--lookback", type=int, default=90)
    p.add_argument("--trend", type=float, default=None, help="override trend_score (0..1)")
    p.add_argument("--volatility", type=float, default=None, help="override volatility (>=0)")
    p.add_argument("--missing-ratio", type=float, default=None, dest="missing_ratio", help="simulate quality (e.g. 0.12)")
    p.add_argument("--data-lag-min", type=int, default=None, dest="data_lag_min", help="simulate data lag minutes")
    p.add_argument("--pretty", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    StrategyCls = _import_strategy(args.strategy)
    strategy = StrategyCls()  # __init__ 無引数想定（必要なら将来拡張）

    extra_ctx: Dict[str, Any] = {}
    if args.trend is not None:
        extra_ctx["trend_score"] = float(args.trend)
    if args.volatility is not None:
        extra_ctx["volatility"] = max(0.0, float(args.volatility))

    fb = build_features(
        symbol=args.symbol,
        timeframe=args.timeframe,
        lookback=int(args.lookback),
        override_missing_ratio=args.missing_ratio,
        override_data_lag_min=args.data_lag_min,
        extra_ctx=extra_ctx,
    )

    result = run_strategy_and_decide(strategy, fb)

    if args.pretty:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
