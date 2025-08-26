# src/plan_data/adapter_to_decision_cli.py
from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any, Dict, Optional, Tuple

import pandas as pd

# plan layer
from plan_data.collector import PlanDataCollector
from plan_data.strategy_adapter import FeatureBundle
from plan_data.adapter_to_decision import run_strategy_and_decide
from plan_data.trace import new_trace_id


def _dyn_load_strategy(target: str) -> Any:
    """
    "pkg.module:ClassName" 形式で戦略クラスをロードしてインスタンス化。
    例: strategies.aurus_singularis:Aurus_Singularis
    """
    if ":" not in target:
        raise ValueError('strategy must be "module.path:ClassName" format')
    mod_name, cls_name = target.split(":", 1)
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    return cls()  # 引数なし前提（必要なら将来拡張）


def _collect(lookback_days: int) -> Tuple[pd.DataFrame, str]:
    """
    収集（PlanDataCollector）。戻り値は (df, trace_id)。
    失敗時は空DF＋新規trace_idを返す。
    """
    try:
        df, tid = PlanDataCollector().collect_all(lookback_days=lookback_days)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df, tid
    except Exception as e:
        print(f"[cli] collector failed: {e}", file=sys.stderr)
    # フォールバック：最小ダミーDF
    tid = new_trace_id(symbol="MULTI", timeframe="1d")
    df = pd.DataFrame({"date": pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=10, freq="D")})
    return df, tid


def _build_context(args: argparse.Namespace, df_tid: str) -> Dict[str, Any]:
    """
    Adapter/Decision 共通で参照する context を組み立て。
    """
    ctx: Dict[str, Any] = {
        "trace_id": df_tid,
        "symbol": args.symbol or "USDJPY",
        "timeframe": args.timeframe or "1d",
        # DecisionEngine が参照するヒント（任意）
        "volatility": float(args.volatility) if args.volatility is not None else 0.20,
        "trend_score": float(args.trend) if args.trend is not None else 0.50,
        # Quality Gate 用のヒント（存在すればadapter側で拾う想定）
        # ここではユーザー指定がなければ未設定＝品質OK扱い
    }
    return ctx


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Run single strategy via Adapter -> Decision and print JSON result."
    )
    p.add_argument(
        "--strategy",
        required=True,
        help='Target strategy as "module.path:ClassName" '
             '(e.g., strategies.aurus_singularis:Aurus_Singularis)',
    )
    p.add_argument("--symbol", default="USDJPY", help="Symbol for context (default: USDJPY)")
    p.add_argument("--timeframe", default="1d", help="Timeframe label for context (default: 1d)")
    p.add_argument("--lookback", type=int, default=120, help="Collector lookback days (default: 120)")

    # DecisionEngine の判断に渡す軽いヒント（任意指定）
    p.add_argument("--trend", type=float, default=None, help="Override trend_score (0..1)")
    p.add_argument("--volatility", type=float, default=None, help="Override volatility (>=0)")

    # Quality Gate に関わる明示指定（任意）：欠損や遅延の手動注入
    p.add_argument("--data-lag-min", type=int, default=None, help="Quality hint: data_lag_min")
    p.add_argument("--missing-ratio", type=float, default=None, help="Quality hint: missing_ratio (0..1)")

    # Model tag (for logging fields)
    p.add_argument("--model-name", default=None, help="Model name tag for infer logging")
    p.add_argument("--model-version", default=None, help="Model version tag for infer logging")

    # JSON 整形
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    args = p.parse_args(argv)

    # 1) 戦略ロード
    try:
        strategy = _dyn_load_strategy(args.strategy)
    except Exception as e:
        print(f"[cli] failed to load strategy: {e}", file=sys.stderr)
        return 2

    # 2) 収集
    df, tid = _collect(lookback_days=args.lookback)

    # 3) FeatureBundle 準備
    ctx = _build_context(args, df_tid=tid)
    if args.data_lag_min is not None:
        ctx["data_lag_min"] = int(args.data_lag_min)
    if args.missing_ratio is not None:
        ctx["missing_ratio"] = float(args.missing_ratio)

    fb = FeatureBundle(df=df, context=ctx)

    # 4) 実行（Adapter -> Decision）
    try:
        result = run_strategy_and_decide(
            strategy=strategy,
            features=fb,
            model_name=args.model_name,
            model_version=args.model_version,
            # conn_str=None → env NOCTRIA_OBS_PG_DSN 依存
        )
    except Exception as e:
        print(f"[cli] run failed: {e}", file=sys.stderr)
        return 3

    # 5) 出力
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
