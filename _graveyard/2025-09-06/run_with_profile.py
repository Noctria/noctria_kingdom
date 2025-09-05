# src/plan_data/run_with_profile.py
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import pandas as pd

# plan layer
from plan_data.strategy_adapter import FeatureBundle, StrategyProposal
from plan_data.profile_loader import load_yaml, resolve_profile, apply_profile_to_bundle, PlanProfile
from plan_data.adapter_to_decision import run_strategy_and_decide

def apply_profile(
    bundle: FeatureBundle,
    config_root: Dict[str, Any],
    *,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
) -> Tuple[FeatureBundle, PlanProfile]:
    """
    既存 profile_loader を利用して、bundle.context に profile 値を注入して返す。
    """
    sym = symbol or (bundle.context.get("symbol") if bundle and bundle.context else None)
    tf  = timeframe or (bundle.context.get("timeframe") if bundle and bundle.context else None)
    prof = resolve_profile(config_root, symbol=sym, timeframe=tf)
    new_bundle = apply_profile_to_bundle(bundle, prof)
    return new_bundle, prof

def run_with_profile(
    strategy: Any,
    bundle: FeatureBundle,
    *,
    profile_yaml_path: str,
    extra_decision_features: Optional[Dict[str, Any]] = None,
    model_name: Optional[str] = None,
    model_version: Optional[str] = None,
    timeout_sec: Optional[float] = None,
    conn_str: Optional[str] = None,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    **strategy_kwargs: Any,
) -> Dict[str, Any]:
    """
    1) YAML から Plan プロファイルを解決し bundle に適用
    2) 戦略を propose_with_logging 経由で実行（adapter 内で品質ゲートが反映された qty へ）
    3) DecisionEngine で最終判断 → dict で返す
    """
    # 1) profile 適用
    config_root = load_yaml(profile_yaml_path)
    prof_bundle, prof = apply_profile(bundle, config_root, symbol=symbol, timeframe=timeframe)

    # 2) 実行（品質ヒントは adapter → adapter_to_decision 間で引き継ぎ）
    result = run_strategy_and_decide(
        strategy,
        prof_bundle,
        engine=None,
        model_name=model_name,
        model_version=model_version,
        timeout_sec=timeout_sec,
        conn_str=conn_str,
        extra_decision_features=extra_decision_features,
        **strategy_kwargs,
    )

    # おまけで適用プロファイルも同梱
    result["profile_applied"] = prof.to_dict()
    return result


# --- 最小の手動テスト ---
if __name__ == "__main__":
    class DummyStrategy:
        def propose(self, features: FeatureBundle, **kw):
            # adapter 側の Quality Gate により qty は縮小される前提。ここはベース数量を返すだけ。
            return StrategyProposal(
                symbol=str(features.context.get("symbol", "USDJPY")),
                direction="LONG",
                qty=float(features.context.get("base_qty", 100.0)),
                confidence=0.8,
                reasons=["dummy ok"],
                meta={},  # adapter 内で quality_action/qty_scale が追記される
            )

    df = pd.DataFrame({"date": pd.date_range("2025-08-01", periods=5, freq="D")})
    fb = FeatureBundle(
        df=df,
        context={
            "symbol": "USDJPY",
            "timeframe": "5m",
            # 品質ゲートが参照する現在の実測値（collector/features 等で埋める想定）
            "data_lag_min": 5,
            "missing_ratio": 0.06,  # プロファイルの閾値次第で SCALE になる想定
        },
    )

    # 例: configs/plan_profiles.yml を用意して実行
    out = run_with_profile(
        DummyStrategy(),
        fb,
        profile_yaml_path="configs/plan_profiles.yml",
        extra_decision_features={"trend_score": 0.72, "volatility": 0.12},
    )
    import json
    print(json.dumps(out, indent=2, ensure_ascii=False))
