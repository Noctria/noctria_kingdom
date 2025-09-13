# noctria_gui/routes/backtest_results.py
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

try:
    import requests  # Airflow REST 呼び出し用（任意）
except Exception:  # pragma: no cover
    requests = None  # type: ignore

router = APIRouter(prefix="/backtests", tags=["backtests"])

# --- 設定 -------------------------------------------------------------
AIRFLOW_SCHEDULER_CONTAINER = os.getenv("AIRFLOW_SCHEDULER_CONTAINER", "noctria_airflow_scheduler")
BACKTEST_BASE_DIR = Path(os.getenv("BACKTEST_BASE_DIR", "/opt/airflow/backtests"))
AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
DAG_ID = os.getenv("NOCTRIA_BACKTEST_DAG_ID", "noctria_backtest_dag")


# --- ユーティリティ -----------------------------------------------------
def _docker_exec_cat(container: str, path: str) -> Optional[bytes]:
    """scheduler コンテナ内のファイルを cat で取得。"""
    try:
        return subprocess.check_output(
            ["docker", "exec", container, "bash", "-lc", f"cat {path}"],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        return None


def _docker_exec_exists(container: str, path: str) -> bool:
    """scheduler コンテナ内でファイル存在チェック。"""
    try:
        out = subprocess.check_output(
            ["docker", "exec", container, "bash", "-lc", f"test -f {path} && echo 1 || echo 0"],
            stderr=subprocess.STDOUT,
        )
        return out.strip() == b"1"
    except Exception:
        return False


def _airflow_latest_run_id() -> Optional[str]:
    """Airflow REST から最新 run_id を取得（失敗時は None）。"""
    if not requests:
        return None
    try:
        url = f"{AIRFLOW_BASE_URL.rstrip('/')}/api/v1/dags/{DAG_ID}/dagRuns"
        params = {"order_by": "-execution_date", "limit": 1}
        auth = (AIRFLOW_USER, AIRFLOW_PASSWORD) if (AIRFLOW_USER and AIRFLOW_PASSWORD) else None
        headers = {}
        token = os.getenv("AIRFLOW_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            auth = None
        resp = requests.get(url, params=params, auth=auth, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        runs = data.get("dag_runs") or []
        if not runs:
            return None
        return runs[0].get("dag_run_id")
    except Exception:
        return None


def _guess_mime_from_name(name: str) -> str:
    if name.endswith(".json"):
        return "application/json; charset=utf-8"
    if name.endswith(".html"):
        return "text/html; charset=utf-8"
    if name.endswith(".csv"):
        return "text/csv; charset=utf-8"
    if name.endswith(".txt"):
        return "text/plain; charset=utf-8"
    return "application/octet-stream"


# --- API: JSON/CONF/ARTIFACT -------------------------------------------
@router.get("/api/latest")
async def api_backtests_latest():
    run_id = _airflow_latest_run_id()
    if not run_id:
        return JSONResponse({"ok": False, "error": "latest run_id not found"}, status_code=404)
    return JSONResponse({"ok": True, "run_id": run_id})


@router.get("/api/{run_id}/json")
async def api_backtests_json(run_id: str):
    path = f"{BACKTEST_BASE_DIR}/{run_id}/result.json"
    content = _docker_exec_cat(AIRFLOW_SCHEDULER_CONTAINER, path)
    if not content:
        raise HTTPException(status_code=404, detail="result.json not found")
    try:
        obj = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"invalid json: {e}")
    return JSONResponse({"ok": True, "data": obj})


@router.get("/api/{run_id}/conf")
async def api_backtests_conf(run_id: str):
    path = f"{BACKTEST_BASE_DIR}/{run_id}/conf.json"
    content = _docker_exec_cat(AIRFLOW_SCHEDULER_CONTAINER, path)
    if not content:
        raise HTTPException(status_code=404, detail="conf.json not found")
    try:
        obj = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"invalid json: {e}")
    return JSONResponse({"ok": True, "data": obj})


@router.get("/api/{run_id}/artifact/{name:path}")
async def api_backtests_artifact(run_id: str, name: str):
    safe_name = name.replace("..", "").lstrip("/")
    path = f"{BACKTEST_BASE_DIR}/{run_id}/{safe_name}"
    content = _docker_exec_cat(AIRFLOW_SCHEDULER_CONTAINER, path)
    if not content:
        raise HTTPException(status_code=404, detail="artifact not found")
    return Response(content, media_type=_guess_mime_from_name(safe_name))


# --- HTML ビュー --------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
async def list_backtests(request: Request):
    run_id = _airflow_latest_run_id()
    runs: List[Dict[str, Any]] = []
    if run_id:
        runs.append({"run_id": run_id, "started": "?"})

    render = getattr(request.app.state, "render_template", None)
    if render:
        return HTMLResponse(render(request, "backtests.html", runs=runs))
    return HTMLResponse(f"<pre>{json.dumps(runs, ensure_ascii=False, indent=2)}</pre>")


@router.get("/{run_id}", response_class=HTMLResponse)
async def run_root_redirect(run_id: str):
    # /backtests/{run_id} -> /report
    return HTMLResponse(
        content=f'<meta http-equiv="refresh" content="0; url=/backtests/{run_id}/report">',
        status_code=307,
    )


@router.get("/{run_id}/report", response_class=HTMLResponse)
async def backtests_report_html(request: Request, run_id: str):
    """HUD スタイルのレポート。存在する成果物だけをリンク表示。"""

    def _load_json(name: str) -> Optional[Dict[str, Any]]:
        p = f"{BACKTEST_BASE_DIR}/{run_id}/{name}"
        b = _docker_exec_cat(AIRFLOW_SCHEDULER_CONTAINER, p)
        if not b:
            return None
        try:
            return json.loads(b.decode("utf-8"))
        except Exception:
            return None

    result = _load_json("result.json")
    conf = _load_json("conf.json") or {}

    # 成果物の有無フラグ
    artifacts = {
        "result_csv": _docker_exec_exists(AIRFLOW_SCHEDULER_CONTAINER, f"{BACKTEST_BASE_DIR}/{run_id}/result.csv"),
        "stdout_txt": _docker_exec_exists(AIRFLOW_SCHEDULER_CONTAINER, f"{BACKTEST_BASE_DIR}/{run_id}/stdout.txt"),
    }

    render = getattr(request.app.state, "render_template", None)
    if not render:
        body = {"run_id": run_id, "result": result, "conf": conf, "artifacts": artifacts}
        return HTMLResponse(f"<pre>{json.dumps(body, ensure_ascii=False, indent=2)}</pre>")

    return HTMLResponse(
        render(request, "backtest_report.html", run_id=run_id, result=result, conf=conf, artifacts=artifacts)
    )
