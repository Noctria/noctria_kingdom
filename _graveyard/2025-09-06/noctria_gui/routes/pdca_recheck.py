# noctria_gui/routes/pdca_recheck.py
# -*- coding: utf-8 -*-
"""
🔁 PDCA Recheck Routes (single & bulk) — v2.4

提供エンドポイント:
- POST /pdca/recheck        : 単一戦略の再評価トリガ（Airflow REST推奨, 成功時は /strategies/detail/{name} へ 303）
- POST /pdca/recheck_all    : 期間/フィルタで抽出した複数戦略を一括トリガ（ルール通過のみ）

強化点:
- Airflow連携は src/core/airflow_client.make_airflow_client() を利用（未配備時はダミー応答で起動継続）
- 観測ログ (obs_infer_calls) は best-effort（未配備でも本処理継続）
- decision ledger (src/core/decision_registry.py) があれば accepted/started/completed/failed を記録
- 戦略ファイルの存在確認は .py/.json 両対応、veritas_generated/ および strategies/ を探索
- ✅ RulesEngine による「統治ルール実行ログ」を組み込み（drawdown guard）
  - 単体: dd_current / dd_threshold を Form で受け、NGなら 409 (blocked_by_rule)
  - 一括: dd_threshold(Query) と dd_current_map(Body, 任意) を用意、通過のみトリガ
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import uuid
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from fastapi import APIRouter, Body, Form, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# ------------------------------------------------------------
# パス/設定
# ------------------------------------------------------------
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parents[2]  # <repo_root>

# path_config が無い環境でも落ちないようにフォールバック
try:
    from src.core.path_config import (
        STRATEGIES_DIR,
        NOCTRIA_GUI_TEMPLATES_DIR,
        PDCA_LOG_DIR as _PDCA_LOG_DIR_SETTING,
    )  # type: ignore
except Exception:  # pragma: no cover
    STRATEGIES_DIR = PROJECT_ROOT / "src" / "strategies"
    NOCTRIA_GUI_TEMPLATES_DIR = PROJECT_ROOT / "noctria_gui" / "templates"
    _PDCA_LOG_DIR_SETTING = None

PDCA_DIR = Path(_PDCA_LOG_DIR_SETTING) if _PDCA_LOG_DIR_SETTING else (PROJECT_ROOT / "data" / "pdca_logs" / "veritas_orders")
PDCA_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/pdca", tags=["PDCA"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

DEFAULT_SINGLE_RECHECK_DAG = os.getenv("AIRFLOW_DAG_RECHECK_SINGLE", "veritas_eval_single_dag")
BULK_RECHECK_DAG = os.getenv("AIRFLOW_DAG_RECHECK_BULK", "veritas_recheck_dag")
SCHEMA_VERSION = "2025-08-01"

# Airflow REST クライアント（未配備でも落とさない）
try:
    from src.core.airflow_client import make_airflow_client  # type: ignore
except Exception:  # pragma: no cover
    make_airflow_client = None  # type: ignore

# 観測ログ（オプショナル）
try:
    from src.plan_data.observability import ensure_tables, log_infer_call  # type: ignore
except Exception:  # pragma: no cover
    ensure_tables = None
    log_infer_call = None  # type: ignore

# decision ledger（オプショナル）
try:
    from src.core.decision_registry import create_decision, append_event  # type: ignore
except Exception:  # pragma: no cover
    create_decision = None  # type: ignore
    append_event = None  # type: ignore

# 統治ルール（drawdown guard）
try:
    from src.core.rules_engine import RulesEngine  # type: ignore
except Exception:  # pragma: no cover
    RulesEngine = None  # type: ignore


# ------------------------------------------------------------
# ユーティリティ
# ------------------------------------------------------------
def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _obs_safe_log(trace_id: str, ai_name: str, params: Dict[str, Any], metrics: Dict[str, Any], status: str, note: str) -> None:
    if ensure_tables and log_infer_call:
        try:
            ensure_tables()
            now_iso = _now_utc_iso()
            log_infer_call(
                trace_id=trace_id,
                ai_name=ai_name,
                started_at=now_iso,
                ended_at=now_iso,
                params_json=params,
                metrics_json=metrics,
                status=status,
                note=note,
            )
        except Exception:
            # 観測ログ失敗は本処理に影響させない
            pass


def _policy_snapshot() -> Dict[str, Any]:
    try:
        from src.core.policy_engine import get_snapshot  # type: ignore
        return dict(get_snapshot())
    except Exception:
        return {}


def _ledger_issue(kind: str, issued_by: str, intent: Dict[str, Any]) -> Optional[str]:
    if not create_decision:
        return None
    try:
        d = create_decision(kind, issued_by=issued_by, intent=intent, policy_snapshot=_policy_snapshot())
        return d.decision_id
    except Exception:
        return None


def _ledger_event(decision_id: Optional[str], phase: str, payload: Dict[str, Any]) -> None:
    if not decision_id or not append_event:
        return
    try:
        append_event(decision_id, phase, payload)
    except Exception:
        pass


def _strategy_candidates(name: str) -> List[Path]:
    """
    戦略ファイルの候補（存在チェック用）
    - veritas_generated/{name}.py / .json
    - strategies/{name}.py / .json
    """
    vg = STRATEGIES_DIR / "veritas_generated"
    return [
        vg / f"{name}.py",
        vg / f"{name}.json",
        STRATEGIES_DIR / f"{name}.py",
        STRATEGIES_DIR / f"{name}.json",
    ]


def _strategy_exists(name: str) -> bool:
    return any(p.exists() for p in _strategy_candidates(name))


def _parse_ymd(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        y, m, d = s.split("-")
        return datetime(int(y), int(m), int(d))
    except Exception:
        return None


def _read_candidate_strategies(
    date_from: Optional[str],
    date_to: Optional[str],
    max_files: int = 120,
    max_targets: int = 50,
) -> List[str]:
    """
    data/pdca_logs/veritas_orders/rechecks_*.csv を新しい順に走査、期間内に評価された strategy を収集。
    - csv.DictReader で安全に読み込み
    - pandas 不要・重複除去・最大件数制限あり
    """
    df = _parse_ymd(date_from)
    dt = _parse_ymd(date_to)

    try:
        files = sorted(PDCA_DIR.glob("rechecks_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)[:max_files]
    except Exception:
        files = []

    seen: set[str] = set()
    out: List[str] = []

    for fp in files:
        try:
            with fp.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    strategy = (row.get("strategy") or "").strip()
                    if not strategy or strategy in seen:
                        continue

                    # 期間フィルタ（evaluated_at があれば利用）
                    ok = True
                    if df or dt:
                        ts = (row.get("evaluated_at") or row.get("timestamp") or "").strip()
                        if ts:
                            try:
                                d = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                                if df and d < df.date():
                                    ok = False
                                if dt and d > dt.date():
                                    ok = False
                            except Exception:
                                pass
                    if not ok:
                        continue

                    seen.add(strategy)
                    out.append(strategy)
                    if len(out) >= max_targets:
                        break
        except Exception:
            continue

        if len(out) >= max_targets:
            break

    return out


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


# ------------------------------------------------------------
# Airflow トリガ（CLIフォールバックも用意: 現状未使用）
# ------------------------------------------------------------
def _airflow_trigger_via_cli(dag_id: str, conf: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
    try:
        run_id = f"manual__noctria__{conf.get('decision_id','unknown')}"
        cmd = ["airflow", "dags", "trigger", dag_id, "--run-id", run_id, "--conf", json.dumps(conf, ensure_ascii=False)]
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        ok = cp.returncode == 0
        msg = cp.stdout.strip() if ok else (cp.stderr.strip() or cp.stdout.strip())
        return ok, f"CLI: {msg}", run_id if ok else None
    except Exception as e:
        return False, f"CLI error: {e}", None


# ------------------------------------------------------------
# ルール評価: drawdown guard
# ------------------------------------------------------------
_RULES = RulesEngine() if RulesEngine else None

def _evaluate_precheck(strategy: str,
                       current_dd: float,
                       dd_threshold: float,
                       decision_id: Optional[str],
                       trace_id: Optional[str]) -> bool:
    """
    再評価実施前の統治ルールチェック。
    RulesEngine が無い環境では True（通過）として処理継続。
    """
    if not _RULES:
        return True
    try:
        return _RULES.evaluate_drawdown_guard(
            strategy_name=strategy,
            current_dd=current_dd,
            threshold=dd_threshold,
            decision_id=decision_id,
            trace_id=trace_id,
            trigger="pdca_recheck",
        )
    except Exception:
        # ルール評価失敗時はブロックせず通過（運用停止を避ける）
        return True


# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@router.post("/recheck")
async def recheck_strategy(
    strategy_name: str = Form(..., description="戦略名"),
    dd_current: float = Form(0.0, description="現在ドローダウン（%）"),
    dd_threshold: float = Form(5.0, description="許容ドローダウン閾値（%）"),
):
    """
    単一戦略の再評価を Airflow（REST）でトリガ。
    - 前段で drawdown guard を評価（NGなら409）
    - 成功時は /strategies/detail/{strategy_name} へ 303 Redirect
    """
    if not _strategy_exists(strategy_name):
        return JSONResponse(status_code=404, content={"detail": f"戦略が存在しません: {strategy_name}", "strategy_name": strategy_name})

    dag_id = DEFAULT_SINGLE_RECHECK_DAG.strip()
    trace_id = str(uuid.uuid4())
    decision_id: Optional[str] = _ledger_issue(
        kind="recheck",
        issued_by="ui",
        intent={"strategy": strategy_name, "reason": "single_recheck"},
    )
    _ledger_event(decision_id, "accepted", {"endpoint": "/pdca/recheck"})

    # ✅ 統治ルールチェック
    ok_rule = _evaluate_precheck(
        strategy=strategy_name,
        current_dd=_to_float(dd_current),
        dd_threshold=_to_float(dd_threshold, 5.0),
        decision_id=decision_id,
        trace_id=trace_id,
    )
    if not ok_rule:
        # ブロックを明示返却（GUI側でも扱いやすい）
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "blocked_by_rule": True,
                "rule": "risk.stop_drawdown",
                "strategy": strategy_name,
                "decision_id": decision_id or "",
                "trace_id": trace_id,
                "ts": _now_utc_iso(),
                "reason": f"current_dd={dd_current} exceeds threshold={dd_threshold}",
            },
        )

    conf: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "trigger_source": "GUI",
        "trace_id": trace_id,
        "requested_at": _now_utc_iso(),
        "mode": "strategy",
        "strategy_name": strategy_name,
        "reason": "single_recheck",
        "dry_run": False,
        "decision_id": decision_id or "NO_DECISION_ID",
        "caller": "ui",
        # ルール実行時に使ったパラメータも残す
        "dd_current": _to_float(dd_current),
        "dd_threshold": _to_float(dd_threshold, 5.0),
    }
    _ledger_event(decision_id, "started", {"dag_id": dag_id, "conf": conf})

    # Airflow トリガ（REST / ダミー）
    try:
        if make_airflow_client:
            client = make_airflow_client()
            res = client.trigger_dag_run(
                dag_id=dag_id,
                conf=conf,
                note=f"Single Recheck from GUI (strategy={strategy_name}, trace_id={trace_id})",
            )
            dag_run_id = res.get("dag_run_id")
        else:
            # ダミー応答（Airflow未配備時の観測テスト用）
            dag_run_id = f"dummy__{uuid.uuid4()}"
            res = {"status": "dummy", "dag_run_id": dag_run_id}

        _obs_safe_log(
            trace_id=trace_id,
            ai_name="PDCA_SingleRecheckTrigger",
            params={"dag_id": dag_id, **conf},
            metrics={"dag_run_id": dag_run_id or "", "response": res},
            status="success",
            note="GUI trigger single recheck",
        )
        _ledger_event(decision_id, "completed", {"dag_run_id": dag_run_id, "response": res})

    except Exception as e:
        _obs_safe_log(
            trace_id=trace_id,
            ai_name="PDCA_SingleRecheckTrigger",
            params={"dag_id": dag_id, **conf},
            metrics={"error": str(e)},
            status="failed",
            note="GUI trigger single recheck failed",
        )
        _ledger_event(decision_id, "failed", {"error": str(e)})
        return JSONResponse(status_code=500, content={"detail": f"Airflow DAGトリガー失敗: {str(e)}", "strategy_name": strategy_name})

    # ✅ Redirect: /strategies/detail/{name}?trace_id=...&decision_id=...
    safe_name = urllib.parse.quote(strategy_name, safe="")
    query = urllib.parse.urlencode({"trace_id": trace_id, "decision_id": decision_id or ""})
    return RedirectResponse(url=f"/strategies/detail/{safe_name}?{query}", status_code=303)


@router.post("/recheck_all")
async def recheck_all(
    reason: str = Query("", description="一括再評価の理由（任意）"),
    filter_date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    filter_date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    max_targets: int = Query(30, ge=1, le=200, description="最大トリガ件数（安全上限あり）"),
    dd_threshold: float = Query(5.0, description="許容ドローダウン閾値（%）"),
    dd_current_map: Optional[Dict[str, float]] = Body(None, embed=True, description="戦略ごとの現在DD（%）, 例: {'A':4.2,'B':6.1}"),
) -> JSONResponse:
    """
    期間で抽出された複数戦略を対象に Airflow を順次トリガ。
    - 各戦略に対して drawdown guard を評価し、通過したものだけトリガ
    - decision_id は戦略ごとに自動発行
    - 失敗しても全体は続行
    """
    strategies = _read_candidate_strategies(filter_date_from, filter_date_to, max_targets=max_targets)
    if not strategies:
        return JSONResponse({"ok": True, "message": "対象戦略が見つかりませんでした。", "triggered": 0, "results": []})

    results: List[Dict[str, Any]] = []
    dag_id = BULK_RECHECK_DAG.strip()
    dd_map = dd_current_map or {}

    for s in strategies:
        decision_id = _ledger_issue(
            kind="recheck",
            issued_by="ui",
            intent={"strategy": s, "reason": reason, "filter": {"from": filter_date_from, "to": filter_date_to}},
        )
        _ledger_event(decision_id, "accepted", {"endpoint": "/pdca/recheck_all"})

        trace_id = str(uuid.uuid4())
        cur_dd = _to_float(dd_map.get(s, 0.0))

        # ✅ 統治ルールチェック
        ok_rule = _evaluate_precheck(
            strategy=s,
            current_dd=cur_dd,
            dd_threshold=_to_float(dd_threshold, 5.0),
            decision_id=decision_id,
            trace_id=trace_id,
        )
        if not ok_rule:
            results.append({"strategy": s, "ok": False, "blocked_by_rule": True, "reason": "drawdown_guard", "current_dd": cur_dd})
            _ledger_event(decision_id, "failed", {"blocked_by_rule": True, "rule": "risk.stop_drawdown", "current_dd": cur_dd})
            continue

        conf = {
            "schema_version": SCHEMA_VERSION,
            "trigger_source": "GUI",
            "trace_id": trace_id,
            "requested_at": _now_utc_iso(),
            "mode": "strategy",
            "strategy_name": s,
            "reason": reason or "",
            "dry_run": False,
            "decision_id": decision_id or "NO_DECISION_ID",
            "caller": "ui",
            "dd_current": cur_dd,
            "dd_threshold": _to_float(dd_threshold, 5.0),
        }
        _ledger_event(decision_id, "started", {"dag_id": dag_id, "conf": conf})

        try:
            if make_airflow_client:
                client = make_airflow_client()
                res = client.trigger_dag_run(
                    dag_id=dag_id,
                    conf=conf,
                    note=f"Bulk Recheck from GUI (strategy={s}, trace_id={trace_id})",
                )
                dag_run_id = res.get("dag_run_id")
            else:
                dag_run_id = f"dummy__{uuid.uuid4()}"
                res = {"status": "dummy", "dag_run_id": dag_run_id}

            _obs_safe_log(
                trace_id=trace_id,
                ai_name="PDCA_BulkRecheckTrigger",
                params={"dag_id": dag_id, **conf},
                metrics={"dag_run_id": dag_run_id or "", "response": res},
                status="success",
                note="GUI trigger bulk recheck",
            )
            _ledger_event(decision_id, "completed", {"dag_run_id": dag_run_id, "response": res})

            results.append({"strategy": s, "ok": True, "message": "Triggered", "dag_run_id": dag_run_id, "decision_id": decision_id})
        except Exception as e:
            _obs_safe_log(
                trace_id=trace_id,
                ai_name="PDCA_BulkRecheckTrigger",
                params={"dag_id": dag_id, **conf},
                metrics={"error": str(e)},
                status="failed",
                note="GUI trigger bulk recheck failed",
            )
            _ledger_event(decision_id, "failed", {"error": str(e)})

            results.append({"strategy": s, "ok": False, "message": f"Trigger failed: {e}", "dag_run_id": None, "decision_id": decision_id})

    succeeded = sum(1 for r in results if r["ok"])
    failed = len(results) - succeeded

    return JSONResponse(
        {
            "ok": failed == 0,
            "message": f"一括再評価を開始しました（成功 {succeeded} / 失敗 {failed} / 対象 {len(results)}）。",
            "triggered": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
            "filters": {"from": filter_date_from, "to": filter_date_to},
            "dd_threshold": _to_float(dd_threshold, 5.0),
        }
    )


# 参考: 履歴ページ（テンプレが無い環境でも起動を止めない）
@router.get("/history", include_in_schema=False)
async def pdca_history(request: Request):
    tpl = Path(NOCTRIA_GUI_TEMPLATES_DIR) / "pdca" / "history.html"
    if not tpl.exists():
        return JSONResponse({"ok": True, "message": "history.html not found (placeholder)."})
    return templates.TemplateResponse("pdca/history.html", {"request": request})
