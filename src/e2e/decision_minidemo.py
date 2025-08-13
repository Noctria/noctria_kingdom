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
import importlib
import importlib.util
from pathlib import Path
import time
import random
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# -----------------------------------------------------------------------------
# import 安定化:
#   - このファイルは src/e2e/decision_minidemo.py に置かれている前提。
#   - <repo>/src を sys.path に追加。
#   - それでも失敗した場合は importlib でファイルパスから直接ロード。
# -----------------------------------------------------------------------------
SRC_DIR = Path(__file__).resolve().parents[1]  # .../<repo>/src
PROJECT_ROOT = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _safe_import(module_name: str) -> Optional[object]:
    """
    3段階で import を試みる:
      1) importlib.import_module(module_name)
      2) importlib.import_module('src.' + module_name)
      3) <repo>/src 直下の .py をファイルパスから直ロード
    失敗したら None を返す。
    """
    # 1) 標準 import
    try:
        return importlib.import_module(module_name)
    except Exception:
        pass

    # 2) src. プレフィックス
    try:
        return importlib.import_module(f"src.{module_name}")
    except Exception:
        pass

    # 3) 直接ロード
    mod_path = SRC_DIR / (module_name.replace(".", "/") + ".py")
    if mod_path.exists():
        spec = importlib.util.spec_from_file_location(module_name, mod_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)  # type: ignore[arg-type]
            return mod
    return None


# --- trace id ---------------------------------------------------------------
mod_trace = _safe_import("plan_data.trace")
if mod_trace and hasattr(mod_trace, "new_trace_id"):
    new_trace_id = getattr(mod_trace, "new_trace_id")
else:
    # 最低限のローカル実装（フォールバック）
    import uuid

    def new_trace_id(*, symbol: str = "MULTI", timeframe: str = "demo") -> str:  # type: ignore[override]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        short = uuid.uuid4().hex[:8]
        sym = "".join(ch for ch in str(symbol).upper() if ch.isalnum() or ch in "_-") or "NA"
        tf = "".join(ch for ch in str(timeframe) if ch.isalnum() or ch in "_-") or "NA"
        return f"{ts}-{sym}-{tf}-{short}"


# --- observability I/O ------------------------------------------------------
mod_obs = _safe_import("plan_data.observability")
if not mod_obs:
    raise SystemExit(
        "Unable to import 'plan_data.observability'.\n"
        f"Checked on sys.path (has src?): {SRC_DIR}\n"
        "Please ensure your working tree has: src/plan_data/observability.py"
    )

ensure_tables = getattr(mod_obs, "ensure_tables")
ensure_views = getattr(mod_obs, "ensure_views", None)
refresh_materialized = getattr(mod_obs, "refresh_materialized", None)
log_plan_run = getattr(mod_obs, "log_plan_run")
log_infer_call = getattr(mod_obs, "log_infer_call")
log_exec_event = getattr(mod_obs, "log_exec_event")

# --- decision engine --------------------------------------------------------
mod_dec = _safe_import("decision.decision_engine")
if not mod_dec:
    raise SystemExit(
        "Unable to import 'decision.decision_engine'.\n"
        "Please ensure your working tree has: src/decision/decision_engine.py"
    )
DecisionEngine = getattr(mod_dec, "DecisionEngine")
DecisionRequest = getattr(mod_dec, "DecisionRequest")

# --- DO層は任意（存在すれば使う）。不足していればダミー実行へフォールバック ---
HAVE_DO = True
try:
    mod_contracts = _safe_import("plan_data.contracts")
    mod_risk = _safe_import("execution.risk_policy")
    mod_exec = _safe_import("execution.order_execution")
    if not (mod_contracts and mod_risk and mod_exec):
        HAVE_DO = False
    else:
        OrderRequest = getattr(mod_contracts, "OrderRequest")
        load_policy = getattr(mod_risk, "load_policy")
        place_order = getattr(mod_exec, "place_order")
except Exception:
    HAVE_DO = False

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
        outputs=pred),
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
    # 0) 観測テーブル・ビューの存在保証（dev/PoC 向け）
    ensure_tables()
    if callable(ensure_views):
        ensure_views()  # タイムライン/レイテンシビューを先に作っておく

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
            if isinstance(do_result, dict) and do_result.get("gate_alerts"):
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

    # 8) ついでに日次レイテンシをリフレッシュ（存在する場合のみ）
    if callable(refresh_materialized):
        try:
            refresh_materialized()
        except Exception:
            pass

    print(f"✅ E2E complete. trace_id={trace_id}")


if __name__ == "__main__":
    main()
