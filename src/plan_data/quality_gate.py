from dataclasses import dataclass
from typing import List
from .contracts import FeatureBundle

@dataclass
class QualityResult:
    ok: bool
    action: str                 # "OK" | "FLAT" | "SCALE"
    qty_scale: float = 1.0
    reasons: List[str] = None

DEFAULT_MAX_DATA_LAG_MIN = 30      # 提案⑤ 初期値
DEFAULT_MAX_MISSING_RATIO = 0.05   # 提案⑤ 初期値

def evaluate_quality(bundle: FeatureBundle,
                     max_lag_min: int = DEFAULT_MAX_DATA_LAG_MIN,
                     max_missing: float = DEFAULT_MAX_MISSING_RATIO) -> QualityResult:
    ctx = bundle.context
    reasons: List[str] = []
    action = "OK"
    scale = 1.0

    if ctx.data_lag_min > max_lag_min:
        reasons.append(f"data_lag_min={ctx.data_lag_min} > {max_lag_min}")
        action = "FLAT"
    if ctx.missing_ratio > max_missing:
        reasons.append(f"missing_ratio={ctx.missing_ratio:.3f} > {max_missing:.3f}")
        action = "SCALE" if action == "OK" else "FLAT"
        if action == "SCALE":
            # 欠損が閾値超ならリスクを半減（軽減フォールバック）
            scale = max(0.3, 1.0 - (ctx.missing_ratio - max_missing) * 2.0)

    ok = action == "OK"
    return QualityResult(ok=ok, action=action, qty_scale=scale, reasons=reasons or [])
