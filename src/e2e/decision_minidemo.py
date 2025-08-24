# ============================================
# File: src/e2e/decision_minidemo.py
# ============================================
"""
E2E ミニデモ:
Plan(ダミー) -> Infer(ダミー) -> DecisionEngine -> Exec(実行: DO層 or ダミー)
同一 trace_id が obs_* テーブルに連携されることを確認。

実行例:
    python3 -m src.e2e.decision_minidemo
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
import inspect

# ---------------------------------------------------------------------------
# import 安定化:
# ---------------------------------------------------------------------------
SRC_DIR = Path(__file__).resolve().parents[1]  # .../<repo>/src
PROJECT_ROOT = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _safe_import(module_name: str) -> Optional[object]:
    try:
        return importlib.import_module(module_name)
    except Exception:
        pass
    try:
        return importlib.import_module(f"src.{module_name}")
    except Exception:
        pass
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

# --- DO層は任意 ------------------------------------------------------------
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


# --- 互換ロガー（log_infer_call のシグネチャ差吸収） -----------------------
def _log_infer_compat(*, dur_ms: int, trace_id: str, features: Dict[str, Any], pred: Dict[str, Any]) -> None:
    fn = log_infer_call
    try:
        sig = inspect.signature(fn)
        names = set(sig.parameters.keys())
        kw: Dict[str, Any] = {}

        # conn_str / dsn 系
        for n in ("conn_str", "dsn", "db", "pg_dsn"):
            if n in names:
                kw[n] = None
                break

        # model 名
        if "model" in names:
            kw["model"] = "DummyPredictor"
        elif "model_name" in names:
            kw["model_name"] = "DummyPredictor"

        # version
        if "ver" in names:
            kw["ver"] = "demo"
        elif "model_version" in names:
            kw["model_version"] = "demo"

        # duration
        if "dur_ms" in names:
            kw["dur_ms"] = int(dur_ms)
        elif "duration_ms" in names:
            kw["duration_ms"] = int(dur_ms)

        # success
        if "success" in names:
            kw["success"] = True

        # staleness
        for n in ("feature_staleness_min", "staleness_min", "features_staleness_min"):
            if n in names:
                kw[n] = 0
                break

        # trace_id
        if "trace_id" in names:
            kw["trace_id"] = trace_id

        # inputs/outputs あれば埋める（ある実装では payload に落ちる）
        if "inputs" in names:
            kw["inputs"] = {"features": features}
        if "outputs" in names:
            kw["outputs"] = pred

        fn(**kw)
        return
    except Exception:
        pass

    # 最終手段：典型的な位置引数シグネチャ
    try:
        fn(None, "DummyPredictor", "demo", int(dur_ms), True, 0, trace_id)  # type: ignore[misc]
    except Exception as e:
        print(f"[WARN] log_infer_call failed with all variants: {e}")


def fake_infer(trace_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
    """予測器ダミー（例: Prometheus の簡易呼び出し代替）"""
    t0_ns = time.perf_counter_ns()
    pred = {
        "next_return_pred": round(random.uniform(-0.003, 0.003), 6),
        "confidence": round(random.uniform(0.4, 0.9), 3),
    }
    dur_ms = max(1, (time.perf_counter_ns() - t0_ns) // 1_000_000)
    _log_infer_compat(dur_ms=dur_ms, trace_id=trace_id, features=features, pred=pred)
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
        ensure_views()

    # 1) トレースID
    trace_id = new_trace_id(symbol=SYMBOL, timeframe="demo")

    # 2) PLAN スパン開始ログ
    log_plan_run(trace_id=trace_id, status="START", started_at=_now_utc(), meta={"demo": "decision_minidemo"})

    # 3) 特徴量（ダミー生成）
    features = fake_plan_features()

    # 4) Infer 呼び出し（ダミー）
    _ = fake_infer(trace_id, features)

    # 5) Decision
    engine = DecisionEngine()
    req = DecisionRequest(trace_id=trace_id, symbol=SYMBOL, features=features)
    result = engine.decide(req)

    # 6) Exec
    if HAVE_DO:
        try:
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
            print(f"[WARN] DO path failed ({e}); fallback to fake_exec.")
            fake_exec(trace_id, result.decision)
    else:
        fake_exec(trace_id, result.decision)

    # 7) PLAN スパン終了ログ
    log_plan_run(trace_id=trace_id, status="END", finished_at=_now_utc())

    # 8) マテビュー更新（存在すれば）
    if callable(refresh_materialized):
        try:
            refresh_materialized()
        except Exception:
            pass

    print(f"✅ E2E complete. trace_id={trace_id}")


if __name__ == "__main__":
    main()
