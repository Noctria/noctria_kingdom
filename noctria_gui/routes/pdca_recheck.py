# noctria_gui/routes/pdca_recheck.py
# -*- coding: utf-8 -*-
"""
🔁 PDCA Recheck Routes (single & bulk) — v2.0

提供エンドポイント:
- POST /pdca/recheck        : 単一戦略の再評価トリガ（Airflow REST via airflow_client）
- POST /pdca/recheck_all    : 期間/フィルタで抽出した複数戦略を一括トリガ

特徴:
- Airflow連携は src/core/airflow_client.make_airflow_client() を利用（REST推奨）
- 観測ログ (obs_infer_calls) への記録は best-effort（未配備でも処理継続）
- decision ledger (src/core/decision_registry.py) があれば accepted/started/completed/failed を記録
- 戦略ファイルの存在確認は .py/.json 両対応、veritas_generated/ および strategies/ を探索
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from fastapi import APIRouter, Body, Form, Query, Request, HTTPException
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

# Airflow REST クライアント
from src.core.airflow_client import make_airflow_client  # type: ignore

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
    pandas 不要・重複除去・最大件数制限あり。
    """
    df = _parse_ymd(date_from)
    dt = _parse_ymd(date_to)

    files = sorted(PDCA_DIR.glob("rechecks_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)[:max_files]
    seen = set()
    out: List[str] = []

    for fp in files:
        try:
            with fp.open("r", encoding="utf-8") as f:
                header = None
                for line in f:
                    line = line.rstrip("\n")
                    if not line:
                        continue
                    cols = line.split(",")
                    if header is None:
                        header = [c.strip() for c in cols]
                        continue
                    row = {header[i]: (cols[i] if i < len(header) else "") for i in range(len(header))}
                    strategy = row.get("strategy", "").strip()
                    if not strategy or strategy in seen:
                        continue

                    ok = True
                    if df or dt:
                        ts = row.get("evaluated_at", "")
                        try:
                            d = datetime.fromisoformat(ts.replace("Z", "+00:00")).date() if ts else None
                            if d:
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
# Routes
# ------------------------------------------------------------
@router.post("/recheck")
async def recheck_strategy(strategy_name: str = Form(...)):
    """
    単一戦略の再評価を Airflow（REST）でトリガ。
    成功時は /statistics/detail?mode=strategy&key={strategy_name} へ 303 Redirect。
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
    }
    _ledger_event(decision_id, "started", {"dag_id": dag_id, "conf": conf})

    try:
        client = make_airflow_client()
        res = client.trigger_dag_run(
            dag_id=dag_id,
            conf=conf,
            note=f"Single Recheck from GUI (strategy={strategy_name}, trace_id={trace_id})",
        )
        dag_run_id = res.get("dag_run_id")

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

    # Redirect to statistics detail
    query = urllib.parse.urlencode({"mode": "strategy", "key": strategy_name, "trace_id": trace_id, "decision_id": decision_id or ""})
    return RedirectResponse(url=f"/statistics/detail?{query}", status_code=303)


@router.post("/recheck_all")
async def recheck_all(
    reason: str = Query("", description="一括再評価の理由（任意）"),
    filter_date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    filter_date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    max_targets: int = Query(30, ge=1, le=200, description="最大トリガ件数（安全上限あり）"),
) -> JSONResponse:
    """
    期間で抽出された複数戦略を対象に Airflow `veritas_recheck_dag` を順次トリガ。
    - decision_id は1件ずつ自動発行
    - 失敗しても全体は続行
    """
    strategies = _read_candidate_strategies(filter_date_from, filter_date_to, max_targets=max_targets)
    if not strategies:
        return JSONResponse({"ok": True, "message": "対象戦略が見つかりませんでした。", "triggered": 0, "results": []})

    results: List[Dict[str, Any]] = []
    dag_id = BULK_RECHECK_DAG.strip()

    for s in strategies:
        decision_id = _ledger_issue(
            kind="recheck",
            issued_by="ui",
            intent={"strategy": s, "reason": reason, "filter": {"from": filter_date_from, "to": filter_date_to}},
        )
        _ledger_event(decision_id, "accepted", {"endpoint": "/pdca/recheck_all"})

        trace_id = str(uuid.uuid4())
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
        }
        _ledger_event(decision_id, "started", {"dag_id": dag_id, "conf": conf})

        try:
            client = make_airflow_client()
            res = client.trigger_dag_run(
                dag_id=dag_id,
                conf=conf,
                note=f"Bulk Recheck from GUI (strategy={s}, trace_id={trace_id})",
            )
            dag_run_id = res.get("dag_run_id")

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
        }
    )


# 参考: 履歴ページ（テンプレが無い環境でも起動を止めない）
@router.get("/history", include_in_schema=False)
async def pdca_history(request: Request):
    tpl = NOCTRIA_GUI_TEMPLATES_DIR / "pdca" / "history.html"
    if not tpl.exists():
        return JSONResponse({"ok": True, "message": "history.html not found (placeholder)."})
    return templates.TemplateResponse("pdca/history.html", {"request": request})
