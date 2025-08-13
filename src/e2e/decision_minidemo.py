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

from src.core.trace import generate_trace_id, now_utc
from src.plan_data.observability import (
    ensure_tables,
    log_plan_run,
    log_infer_call,
    log_exec_event,
)
from src.decision.decision_engine import DecisionEngine, DecisionRequest

SYMBOL = "USDJPY"

def fake_plan_features() -> Dict[str, float]:
    # 既存Plan層の代替ダミー（統合が済むまで）
    return {
        "volatility": round(random.uniform(0.05, 0.35), 3),
        "trend_score": round(random.uniform(0.0, 1.0), 3),
    }

def fake_infer(trace_id: str, features: Dict[str, float]) -> Dict[str, Any]:
    # 予測器ダミー（例: Prometheusの簡易呼び出し代替）
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

def fake_exec(trace_id: str, decision: Dict[str, Any]):
    # 約定APIダミー
    log_exec_event(
        trace_id=trace_id,
        symbol=decision.get("symbol", SYMBOL),
        side="BUY" if decision.get("action") in ("enter_trend", "range_trade") else "FLAT",
        size=10000,
        provider="DummyBroker",
        status="SENT",
        order_id="DUMMY-ORDER-001",
        response={"ok": True},
    )

def main():
    ensure_tables()
    trace_id = generate_trace_id("noctria")

    # --- Plan Run 開始/終了ログ
    log_plan_run(trace_id=trace_id, status="START", started_at=now_utc())
    features = fake_plan_features()
    # ここで本来のPlan層（collector→features→analyzer）に接続

    # --- （任意）Infer 呼び出し
    _ = fake_infer(trace_id, features)

    # --- Decision
    engine = DecisionEngine()
    req = DecisionRequest(trace_id=trace_id, symbol=SYMBOL, features=features)
    result = engine.decide(req)

    # --- Exec（ダミー）
    fake_exec(trace_id, result.decision)

    # --- Plan Run 完了
    log_plan_run(trace_id=trace_id, status="END", finished_at=now_utc())

    print(f"✅ E2E complete. trace_id={trace_id}")

if __name__ == "__main__":
    main()
