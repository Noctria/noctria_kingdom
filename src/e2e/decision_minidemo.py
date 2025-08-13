# ============================================
# File: src/e2e/decision_minidemo.py
# ============================================
"""
E2E ミニデモ:
Plan(ダミー) -> Infer(ダミー) -> DecisionEngine -> Exec(ダミー)
同一 trace_id が obs_* テーブルに連携されることを確認。

実行例:
    python -m src.e2e.decision_minidemo
"""

from __future__ import annotations

import time
import random
from typing import Dict, Any
from datetime import datetime, timezone

from src.plan_data.trace import new_trace_id
from src.plan_data.observability import (
    ensure_tables,
    log_plan_run,
    log_infer_call,
    log_exec_event,
)
from src.decision.decision_engine import DecisionEngine, DecisionRequest

SYMBOL = "USDJPY"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fake_plan_features() -> Dict[str, float]:
    """既存 Plan 層の代替ダミー（collector→features→analyzer の代わり）"""
    return {
        "volatility": round(random.uniform(0.05, 0.35), 3),
        "trend_score": round(random.uniform(0.0, 1.0), 3),
    }


def fake_infer(trace_id: str, features: Dict[str, float]) -> Dict[str, Any]:
    """予測器ダミー（例: Prometheus の簡易呼び出し代替）"""
    t0 = time.time()
    pred = {
        "next_return_pred": round(random.uniform(-0.003, 0.003), 6),
        "confidence": round(random.uniform(0.4, 0.9), 3),
    }
    duration_ms = int((time.time() - t0) * 1000)
    log_infer_call(
        trace_id=trace_id,
        model_name="DummyPredictor",
        duration_ms=duration_ms,
        success=True,
        inputs={"features": features},
        outputs=pred,
    )
    return pred


def fake_exec(trace_id: str, decision: Dict[str, Any]) -> None:
    """約定APIダミー（実送信の代わりに obs_exec_events に記録）"""
    side = "BUY" if decision.get("action") in ("enter_trend", "range_trade") else "FLAT"
    log_exec_event(
        trace_id=trace_id,
        symbol=decision.get("symbol", SYMBOL),
        side=side,
        size=10000,
        provider="DummyBroker",
        status="SENT",
        order_id="DUMMY-ORDER-001",
        response={"ok": True},
    )


def main() -> None:
    # 0) 観測テーブルの存在保証（dev/PoC 向け）
    ensure_tables()

    # 1) トレースID
    trace_id = new_trace_id(symbol=SYMBOL, timeframe="demo")

    # 2) PLAN スパン開始ログ（新API）
    log_plan_run(trace_id=trace_id, status="START", started_at=_now_utc(), meta={"demo": "decision_minidemo"})

    # 3) 特徴量（ダミー生成）※本来は collector→features→analyzer
    features = fake_plan_features()

    # 4) （任意）Infer 呼び出し（ダミー）
    _ = fake_infer(trace_id, features)

    # 5) Decision
    engine = DecisionEngine()
    req = DecisionRequest(trace_id=trace_id, symbol=SYMBOL, features=features)
    result = engine.decide(req)  # NOCTRIA_OBS_PG_DSN が設定されていれば obs_decisions にも記録される

    # 6) Exec（ダミー送信ログ）
    fake_exec(trace_id, result.decision)

    # 7) PLAN スパン終了ログ
    log_plan_run(trace_id=trace_id, status="END", finished_at=_now_utc())

    print(f"✅ E2E complete. trace_id={trace_id}")


if __name__ == "__main__":
    main()
