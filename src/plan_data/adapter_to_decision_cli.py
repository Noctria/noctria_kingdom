# src/plan_data/adapter_to_decision_cli.py
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import re
import sys
from typing import Any, Dict, Optional, Type

# ---- import 経路安定化 ----
try:
    from src.core.path_config import ensure_import_path  # type: ignore
    ensure_import_path()
except Exception:
    pass

# ---- 明示的に src.* で統一 ----
from src.plan_data.collector import PlanDataCollector  # type: ignore
from src.plan_data.strategy_adapter import FeatureBundle  # type: ignore
from src.plan_data.adapter_to_decision import run_strategy_and_decide  # type: ignore


def _snake_to_camel(s: str) -> str:
    # "aurus_singularis" -> "AurusSingularis"
    parts = re.split(r"[_\-\s]+", s)
    return "".join(p.capitalize() for p in parts if p)


def _strip_non_alnum(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", s)


def _find_class_candidates(mod) -> list[str]:
    """モジュール内の 'クラスっぽい' 名前候補を列挙"""
    cands = []
    for name, obj in vars(mod).items():
        if inspect.isclass(obj) and obj.__module__ == mod.__name__:
            cands.append(name)
    # 見つからない時は大文字始まりの呼び出し可能を緩く候補に
    if not cands:
        for name, obj in vars(mod).items():
            if name[:1].isupper() and callable(obj):
                cands.append(name)
    return sorted(set(cands))


def _resolve_strategy_class(mod, cls_name: str) -> Type:
    """
    いくつかのゆるい解決策でクラスを探す。
    優先順:
      1) 完全一致
      2) 非英数除去で一致（Aurus_Singularis -> AurusSingularis）
      3) snake->Camel（aurus_singularis -> AurusSingularis）
      4) 候補一覧から近いもの（大文字小文字無視）
    """
    # 1) 完全一致
    if hasattr(mod, cls_name):
        obj = getattr(mod, cls_name)
        if inspect.isclass(obj) or callable(obj):
            return obj  # type: ignore[return-value]

    # 2) 非英数除去で比較
    want_key = _strip_non_alnum(cls_name).lower()
    for name, obj in vars(mod).items():
        if _strip_non_alnum(name).lower() == want_key and (inspect.isclass(obj) or callable(obj)):
            return obj  # type: ignore[return-value]

    # 3) snake->Camel
    camel = _snake_to_camel(cls_name)
    if hasattr(mod, camel):
        obj = getattr(mod, camel)
        if inspect.isclass(obj) or callable(obj):
            return obj  # type: ignore[return-value]

    # 4) 近い候補（大文字小文字無視の startswith / equals）
    cands = _find_class_candidates(mod)
    low = cls_name.lower()
    for cand in cands:
        if cand.lower() == low:
            return getattr(mod, cand)
    for cand in cands:
        if cand.lower().startswith(low) or low.startswith(cand.lower()):
            return getattr(mod, cand)

    # 見つからなければエラー（候補一覧を表示）
    raise AttributeError(
        f"Class '{cls_name}' not found in module '{mod.__name__}'. "
        f"Available candidates: {', '.join(cands) or '(none)'}"
    )


def _import_strategy(dotted: str):
    """
    例:
      "src.strategies.aurus_singularis:Aurus_Singularis"
      "src.strategies.aurus_singularis:AurusSingularis"
      "src.strategies.levia_tempest:LeviaTempest"
    """
    if ":" not in dotted:
        raise ValueError(f"strategy format must be 'module:ClassName', got: {dotted}")
    mod_name, cls_name = dotted.split(":", 1)
    mod = importlib.import_module(mod_name)
    return _resolve_strategy_class(mod, cls_name)


def build_features(symbol: str, timeframe: str, lookback: int,
                   override_missing_ratio: Optional[float],
                   override_data_lag_min: Optional[int],
                   extra_ctx: Dict[str, Any]) -> FeatureBundle:
    collector = PlanDataCollector()
    df, tid = collector.collect_all(lookback_days=max(lookback, 1))
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
    p.add_argument("--strategy", required=True, help="module:Class (e.g. src.strategies.aurus_singularis:AurusSingularis)")
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
    strategy = StrategyCls()  # __init__ 無引数想定

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
