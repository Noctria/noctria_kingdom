# ============================================
# File: src/e2e/decision_minidemo.py
# ============================================
"""
E2E ミニデモ:
Plan(ダミー) -> Infer(ダミー) -> DecisionEngine -> Exec(実行: DO層 or ダミー)
同一 trace_id が obs_* テーブルに連携されることを確認。

実行例:
    python -m src.e2e.decision_minidemo
"""

from __future__ import annotations

import sys
from pathlib import Path
import time
import random
from typing import Dict, Any
from datetime import datetime, timezone

# -----------------------------------------------------------------------------
# import 安定化:
#   このファイルは src/e2e/decision_minidemo.py に置かれている前提。
#   まず <repo>/src を sys.path に直接追加（単体実行対応）し、
#   あれば core.path_config.ensure_import_path() を呼んで集中管理に委譲。
# -----------------------------------------------------------------------------
SRC_DIR = Path(__file__).resolve().parents[1]  # .../<repo>/src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    # 集中管理（任意）：PROJECT_ROOT / SRC の両方を sys.path に整備
    from core.path_config import ensure_import_path  # type: ignore
    ensure_import_path()
except Exception:
    # 無ければそのまま（上の手動追加で十分動く）
    pass

from plan_data.trace import new_trace_id
from plan_data.observability import (
    ensure_tables,
    log_plan_run,
    log_infer_call,
    log_exec_event,
)
from decision.decision_engine import DecisionEngine, DecisionRequest

# DO層は任意（存在すれば使う）。不足していればダミー実行へフォールバック
HAVE_DO = True
try:
    from plan_data.contracts import OrderRequest
    from execution.risk_policy import load_policy
    from execution.order_execution import place_order
except Exception:
    HAVE_DO = False  # import 失敗時は DO 経路を使わない

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
    result = engine.decide(req)  # NOCTRIA_OBS_PG_DSN が設定されていれば obs_decisions に記録

    # 6) Exec: DO層があれば gate→idempotency→outbox→EXEC（ALERTも出ることがある）
    if HAVE_DO:
        try:
            # qty は大きめにして gate の clamp / ALERT 発火を狙う
            ord_req = OrderRequest(
                symbol=req.symbol,
                intent="LONG" if result.decision.get("action") in ("enter_trend", "range_trade") else "SHORT",
                qty=10000.0,
                order_type="MARKET",
                limit_price=None,
                sources=[],
                trace_id=trace_id,
            )
            policy = load_policy("configs/risk_policy.yml")
            do_result = place_order(order=ord_req, risk_policy=policy, conn_str=None)
            if do_result.get("gate_alerts"):
                print("ALERTS:", do_result["gate_alerts"])
        except Exception as e:
            # DOパスで失敗した場合はフォールバックでダミー実行
            print(f"[WARN] DO path failed ({e}); fallback to fake_exec.")
            fake_exec(trace_id, result.decision)
    else:
        # DO層無し → ダミー実行
        fake_exec(trace_id, result.decision)

    # 7) PLAN スパン終了ログ
    log_plan_run(trace_id=trace_id, status="END", finished_at=_now_utc())

    print(f"✅ E2E complete. trace_id={trace_id}")


if __name__ == "__main__":
    main()
