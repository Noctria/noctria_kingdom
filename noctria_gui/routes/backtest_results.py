# noctria_gui/routes/backtest_results.py
from __future__ import annotations

import base64
import json
import os
import subprocess
import typing as t
from dataclasses import dataclass

from flask import Blueprint, Response, abort, jsonify, make_response, redirect, request

try:
    import requests  # Airflow REST 呼び出し用（任意）
except Exception:  # pragma: no cover
    requests = None  # type: ignore

backtest_bp = Blueprint("backtest_results", __name__)

# --- 設定（環境変数で上書き可） ---------------------------------------------
AIRFLOW_SCHEDULER_CONTAINER = os.getenv("AIRFLOW_SCHEDULER_CONTAINER", "noctria_airflow_scheduler")
BACKTEST_BASE_DIR = os.getenv("BACKTEST_BASE_DIR", "/opt/airflow/backtests")
AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
DAG_ID = os.getenv("NOCTRIA_BACKTEST_DAG_ID", "noctria_backtest_dag")


@dataclass
class FetchResult:
    ok: bool
    content: t.Optional[bytes] = None
    error: t.Optional[str] = None
    mimetype: str = "application/octet-stream"


# --- ユーティリティ -----------------------------------------------------------
def _docker_exec_cat(container: str, path: str) -> FetchResult:
    """
    Docker コンテナ内のファイルを cat で取得。
    - docker CLI 前提（GUIはローカル運用なので基本OK）
    """
    try:
        out = subprocess.check_output(
            ["docker", "exec", container, "bash", "-lc", f"cat {path}"],
            stderr=subprocess.STDOUT,
        )
        return FetchResult(ok=True, content=out)
    except subprocess.CalledProcessError as e:
        return FetchResult(ok=False, error=e.output.decode("utf-8", errors="replace"))
    except FileNotFoundError:
        return FetchResult(ok=False, error="docker command not found (install Docker/ensure PATH)")

def _json_response(data: t.Any, status: int = 200) -> Response:
    return make_response(jsonify(data), status)

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

def _airflow_latest_run_id() -> t.Optional[str]:
    """
    Airflow REST から最新の run_id を取得（失敗時は None）
    """
    if not requests:
        return None
    try:
        url = f"{AIRFLOW_BASE_URL.rstrip('/')}/api/v1/dags/{DAG_ID}/dagRuns"
        # 最新順で 1 件
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

# --- ルート群 -----------------------------------------------------------------
@backtest_bp.route("/api/backtests/latest", methods=["GET"])
def api_backtests_latest() -> Response:
    """
    最新 run_id を返す（Airflow REST を使用）。
    """
    run_id = _airflow_latest_run_id()
    if not run_id:
        return _json_response({"ok": False, "error": "latest run_id not found"}, 404)
    return _json_response({"ok": True, "run_id": run_id})

@backtest_bp.route("/api/backtests/<path:run_id>/json", methods=["GET"])
def api_backtests_json(run_id: str) -> Response:
    """
    result.json を返す（scheduler コンテナから取得）。
    """
    path = f"{BACKTEST_BASE_DIR.rstrip('/')}/{run_id}/result.json"
    fetched = _docker_exec_cat(AIRFLOW_SCHEDULER_CONTAINER, path)
    if not fetched.ok or fetched.content is None:
        return _json_response({"ok": False, "error": fetched.error or "fetch failed"}, 404)
    try:
        obj = json.loads(fetched.content.decode("utf-8"))
    except Exception as e:
        return _json_response({"ok": False, "error": f"invalid json: {e}"}, 500)
    return _json_response({"ok": True, "data": obj})

@backtest_bp.route("/api/backtests/<path:run_id>/conf", methods=["GET"])
def api_backtests_conf(run_id: str) -> Response:
    """
    conf.json を返す。
    """
    path = f"{BACKTEST_BASE_DIR.rstrip('/')}/{run_id}/conf.json"
    fetched = _docker_exec_cat(AIRFLOW_SCHEDULER_CONTAINER, path)
    if not fetched.ok or fetched.content is None:
        return _json_response({"ok": False, "error": fetched.error or "fetch failed"}, 404)
    try:
        obj = json.loads(fetched.content.decode("utf-8"))
    except Exception as e:
        return _json_response({"ok": False, "error": f"invalid json: {e}"}, 500)
    return _json_response({"ok": True, "data": obj})

@backtest_bp.route("/backtests/<path:run_id>/report", methods=["GET"])
def backtests_report_html(run_id: str) -> Response:
    """
    report.html をそのまま返す（text/html）。
    """
    path = f"{BACKTEST_BASE_DIR.rstrip('/')}/{run_id}/report.html"
    fetched = _docker_exec_cat(AIRFLOW_SCHEDULER_CONTAINER, path)
    if not fetched.ok or fetched.content is None:
        # 軽量ランナー未実行などで report.html が無い場合もあるので、ヒントを返す
        return make_response(
            f"<pre>report.html not found for run_id={run_id}\n"
            f"hint: ensure lightweight runner wrote the HTML.\n"
            f"container={AIRFLOW_SCHEDULER_CONTAINER}\npath={path}\n"
            f"error={fetched.error or 'unknown'}</pre>",
            404,
        )
    resp = make_response(fetched.content)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp

@backtest_bp.route("/api/backtests/<path:run_id>/artifact/<path:name>", methods=["GET"])
def api_backtests_artifact(run_id: str, name: str) -> Response:
    """
    任意の成果物（CSV/テキスト等）を返す:
      /api/backtests/<run_id>/artifact/result.csv など
    """
    safe_name = name.replace("..", "").lstrip("/")
    path = f"{BACKTEST_BASE_DIR.rstrip('/')}/{run_id}/{safe_name}"
    fetched = _docker_exec_cat(AIRFLOW_SCHEDULER_CONTAINER, path)
    if not fetched.ok or fetched.content is None:
        return _json_response({"ok": False, "error": fetched.error or "fetch failed"}, 404)
    resp = make_response(fetched.content)
    resp.headers["Content-Type"] = _guess_mime_from_name(safe_name)
    return resp

# --- （任意）最新 run_id の HTML へ誘導 ---------------------------------------
@backtest_bp.route("/backtests/latest", methods=["GET"])
def backtests_latest_redirect() -> Response:
    """
    最新 run_id の report へリダイレクト（report が無ければ JSON エンドポイントへ）。
    """
    run_id = _airflow_latest_run_id()
    if not run_id:
        return make_response("<pre>latest run_id not found</pre>", 404)
    # まず report.html の存在を軽く確認
    path = f"{BACKTEST_BASE_DIR.rstrip('/')}/{run_id}/report.html"
    fetched = _docker_exec_cat(AIRFLOW_SCHEDULER_CONTAINER, path)
    if fetched.ok and fetched.content:
        return redirect(f"/backtests/{run_id}/report", code=302)
    return redirect(f"/api/backtests/{run_id}/json", code=302)


@router.get("/backtests", response_class=HTMLResponse)
async def list_backtests(request: Request):
    # 直近の run_id を Airflow REST から取得してもいいし
    # ローカル backtests_* ディレクトリを走査してもよい
    runs = [
        {"run_id": "manual__2025-09-13T08:37:43.557371", "started": "2025-09-13 08:37"},
        # 実際は os.listdir で生成
    ]
    return templates.TemplateResponse("backtests.html", {"request": request, "runs": runs})

