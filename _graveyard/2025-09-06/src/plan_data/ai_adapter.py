import concurrent.futures as cf
from typing import Callable, Dict
from .contracts import FeatureBundle, StrategyProposal

def propose_with_timeout(fn: Callable[[FeatureBundle], StrategyProposal],
                         bundle: FeatureBundle, timeout_ms: int, fallback_strategy: str) -> StrategyProposal:
    timeout_s = max(0.05, timeout_ms / 1000.0)
    with cf.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn, bundle)
        try:
            return fut.result(timeout=timeout_s)
        except Exception:
            # タイムアウト/例外は FLAT で返す（観測は別途）
            return StrategyProposal(
                strategy=fallback_strategy, intent="FLAT", qty_raw=0.0,
                confidence=0.0, risk_score=0.5, reasons=["timeout_or_error"], latency_ms=int(timeout_ms),
                trace_id=bundle.trace_id
            )
