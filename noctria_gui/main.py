#!/usr/bin/env python3
# coding: utf-8
"""
Noctria Kingdom GUI - main entrypoint

- ルーター統合（存在しないものは安全にスキップ）
- 静的/テンプレートの安全マウント
- 例外ハンドラ / healthz / ルートリダイレクト
- セッション（HUDトースト等で request.session を利用）

今回のポイント
- .env を確実に読み込む（PROJECT_ROOT/.env, noctria_gui/.env の順で）
- PDCAサマリーDB: 起動時に ensure_tables()/healthcheck() を best-effort 実行
- path_config 不在時でもフォールバックして起動継続
- Jinja2 に from_json / tojson フィルタを登録し、env を app.state.jinja_env に公開
- HAS_DASHBOARD を緩やかに判定（module名に ".dashboard" を含む場合を許容）
- Act手動トリガ／Decision/Tags/Airflow 履歴ビューを配線
- トースト閉じる用の /__clear_toast を追加
- 🆕 GUIレイテンシ観測ミドルウェア（リングバッファ＋任意でJSONL追記）
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from collections import deque
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from noctria_gui.routes.statistics import router as statistics_router
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse

# ---------------------------------------------------------------------------
# import path: <repo_root>/src を最優先に追加
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# ---------------------------------------------------------------------------
# .env 読み込み（python-dotenv が無くても起動継続）
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore
    for _env_path in (PROJECT_ROOT / ".env", PROJECT_ROOT / "noctria_gui" / ".env"):
        if _env_path.exists():
            load_dotenv(_env_path, override=False)
except Exception:
    pass

# ---------------------------------------------------------------------------
# 集中管理パス設定（path_config が無くてもフォールバック）
# ---------------------------------------------------------------------------
_FALLBACK_STATIC_DIR = PROJECT_ROOT / "noctria_gui" / "static"
_FALLBACK_TEMPLATES_DIR = PROJECT_ROOT / "noctria_gui" / "templates"
try:
    from src.core.path_config import (  # type: ignore
        NOCTRIA_GUI_STATIC_DIR as _STATIC_DIR,
        NOCTRIA_GUI_TEMPLATES_DIR as _TEMPLATES_DIR,
    )
    NOCTRIA_GUI_STATIC_DIR: Path = Path(str(_STATIC_DIR))
    NOCTRIA_GUI_TEMPLATES_DIR: Path = Path(str(_TEMPLATES_DIR))
except Exception:
    NOCTRIA_GUI_STATIC_DIR = _FALLBACK_STATIC_DIR
    NOCTRIA_GUI_TEMPLATES_DIR = _FALLBACK_TEMPLATES_DIR

# ---------------------------------------------------------------------------
# logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("noctria_gui.main")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="2.6.2",
)

# セッション
SESSION_SECRET = os.getenv("NOCTRIA_SESSION_SECRET", "noctria-dev-only-change-me")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# ---------------------------------------------------------------------------
# 静的/テンプレートの安全マウント
# ---------------------------------------------------------------------------
if NOCTRIA_GUI_STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
    logger.info("Static mounted: %s", NOCTRIA_GUI_STATIC_DIR)
else:
    logger.warning("Static dir not found: %s (skip mounting)", NOCTRIA_GUI_STATIC_DIR)

_tpl_dir = NOCTRIA_GUI_TEMPLATES_DIR if NOCTRIA_GUI_TEMPLATES_DIR.exists() else _FALLBACK_TEMPLATES_DIR
templates = Jinja2Templates(directory=str(_tpl_dir))
logger.info("Templates dir: %s", _tpl_dir)

def from_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value

def tojson_filter(value: Any, indent: int = 2) -> Markup:
    try:
        return Markup(json.dumps(value, ensure_ascii=False, indent=indent))
    except Exception:
        return Markup("null")

templates.env.filters["from_json"] = from_json
templates.env.filters["tojson"] = tojson_filter

# ルーターから参照できるように公開
app.state.jinja_env = templates.env

def render_template(request: Request, template_name: str, **ctx: Any) -> str:
    tmpl = templates.env.get_template(template_name)
    return tmpl.render(request=request, **ctx)

app.state.render_template = render_template

# ---------------------------------------------------------------------------
# 🆕 GUIレイテンシ観測: リングバッファ & ミドルウェア（任意でJSONL追記）
# ---------------------------------------------------------------------------
class _LatencyStore:
    def __init__(self, maxlen: int = 10000):
        self._dq = deque(maxlen=maxlen)

    def add(self, rec: Dict[str, Any]) -> None:
        self._dq.append(rec)

    def snapshot(self, limit: int = 300) -> list[Dict[str, Any]]:
        return list(self._dq)[-limit:]

if not hasattr(app.state, "latency_store"):
    app.state.latency_store = _LatencyStore(maxlen=10000)

LAT_LOG_PATH = os.getenv("NOCTRIA_LATENCY_LOG", "logs/observability_gui_latency.jsonl")

@app.middleware("http")
async def latency_middleware(request: Request, call_next):
    start = time.perf_counter()
    resp = await call_next(request)
    dur_ms = (time.perf_counter() - start) * 1000.0

    path = request.url.path
    # 自分自身や静的は除外
    if not (path.startswith("/static") or path == "/favicon.ico"):
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int((time.time()%1)*1000):03d}Z",
            "method": request.method,
            "path": path,
            "status": getattr(resp, "status_code", None),
            "duration_ms": round(dur_ms, 3),
            "trace_id": request.headers.get("X-Trace-Id"),
        }
        try:
            request.app.state.latency_store.add(rec)
            if LAT_LOG_PATH:
                os.makedirs(os.path.dirname(LAT_LOG_PATH), exist_ok=True)
                with open(LAT_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
    return resp

# ---------------------------------------------------------------------------
# PDCAサマリーDB: ensure/health（best-effort）
# ---------------------------------------------------------------------------
_SUMMARY_AVAILABLE = False
_SUMMARY_DSN = None
try:
    from src.plan_data import pdca_summary_service as _P  # type: ignore
    _SUMMARY_AVAILABLE = True
    try:
        _SUMMARY_DSN = getattr(_P, "_get_dsn", lambda: None)()
    except Exception:
        _SUMMARY_DSN = None
except Exception as _e:
    logger.warning("PDCA summary service not available: %r", _e)
    _SUMMARY_AVAILABLE = False

@app.on_event("startup")
def _startup_pdca_summary() -> None:
    if not _SUMMARY_AVAILABLE:
        return
    try:
        _P.ensure_tables(verbose=False)
        ok, msg = _P.healthcheck()
        logger.info(("✅" if ok else "⚠️") + " PDCA summary DB: %s", msg)
    except Exception as e:
        logger.warning("PDCA summary DB init skipped: %r", e)

# ---------------------------------------------------------------------------
# ルーター安全取り込みユーティリティ
# ---------------------------------------------------------------------------
HAS_DASHBOARD = False

def _safe_include(
    module_path: str,
    attr: str = "router",
    *,
    prefix: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
) -> bool:
    """
    include_router の安全ラッパー。
    - attr で指定した属性（既定: router）を取りに行く
    - 失敗したら警告だけ出してスキップ
    - ".dashboard" を含むモジュールは HAS_DASHBOARD を True に
    """
    global HAS_DASHBOARD
    try:
        mod = import_module(module_path)
        router = getattr(mod, attr)
        if prefix or tags:
            app.include_router(router, prefix=prefix or "", tags=list(tags or []))
        else:
            app.include_router(router)
        logger.info("Included router: %s (%s)", module_path, attr)
        if ".dashboard" in module_path:
            HAS_DASHBOARD = True
        return True
    except Exception as e:
        logger.warning("Skip router '%s' (%s): %s", module_path, attr, e)
        return False

logger.info("Integrating routers...")

# 主要ルーター群（存在しなくてもスキップ可）
_safe_include("noctria_gui.routes.home_routes")
_safe_include("noctria_gui.routes.dashboard")
_safe_include("noctria_gui.routes.plan_news")   # Plan News 画面 & API

# 王系
_safe_include("noctria_gui.routes.king_routes")
_safe_include("noctria_gui.routes.trigger")
_safe_include("noctria_gui.routes.hermes")

# Act/ログ系
_safe_include("noctria_gui.routes.act_history")
_safe_include("noctria_gui.routes.act_history_detail")
_safe_include("noctria_gui.routes.logs_routes")
_safe_include("noctria_gui.routes.upload_history")
_safe_include("noctria_gui.routes.act_adopt")

# --- PDCA関連 ---
_safe_include("noctria_gui.routes.pdca")
_safe_include("noctria_gui.routes.pdca_recheck")
_safe_include("noctria_gui.routes.pdca_routes")
_safe_include("noctria_gui.routes.pdca_summary")
_safe_include("noctria_gui.routes.pdca_recent")
_safe_include("noctria_gui.routes.pdca_widgets")
# API（←これが /pdca/api/* の実体）
_safe_include("noctria_gui.routes.pdca_api")

# 戦略・統計・タグ
_safe_include("noctria_gui.routes.push")
_safe_include("noctria_gui.routes.push_history")
_safe_include("noctria_gui.routes.strategy_routes", prefix="/strategies", tags=["strategies"])
_safe_include("noctria_gui.routes.strategy_detail")
_safe_include("noctria_gui.routes.strategy_heatmap")

_safe_include("noctria_gui.routes.statistics", prefix="/statistics", tags=["statistics"])
_safe_include("noctria_gui.routes.statistics_detail")
_safe_include("noctria_gui.routes.statistics_ranking")
_safe_include("noctria_gui.routes.statistics_scoreboard")
_safe_include("noctria_gui.routes.statistics_tag_ranking")
_safe_include("noctria_gui.routes.statistics_compare")

_safe_include("noctria_gui.routes.tag_summary")
_safe_include("noctria_gui.routes.tag_summary_detail")
_safe_include("noctria_gui.routes.tag_heatmap")
_safe_include("noctria_gui.routes.adoptions")

# AI/DevCycle系
_safe_include("noctria_gui.routes.ai_routes")
_safe_include("noctria_gui.routes.devcycle_history")
_safe_include("noctria_gui.routes.decision_registry")

# Airflow関連
_safe_include("noctria_gui.routes.airflow_runs")

# Git関連
_safe_include("noctria_gui.routes.git_tags")

# ユーティリティ
_safe_include("noctria_gui.routes.path_checker")
_safe_include("noctria_gui.routes.prometheus_routes")
_safe_include("noctria_gui.routes.upload")

# チャット履歴API（循環importのリスクがあるため安全取り込み）
_safe_include("noctria_gui.routes.chat_history_api")
# _safe_include("noctria_gui.routes.chat_api")

# 可観測性ビュー（既存）
_safe_include("noctria_gui.routes.observability")

# ★ レイテンシ可視化ダッシュボード（FastAPI/Flask両対応の柔軟取り込み）
#   - FastAPI: router
#   - 互換エイリアス: bp_obs_latency / obs_bp
#   - Flask Blueprint が置いてあっても include 失敗 → 404 の原因になるため、優先的に 'router' を試す
included = (
    _safe_include("noctria_gui.routes.observability_latency", "router")
    or _safe_include("noctria_gui.routes.observability_latency", "bp_obs_latency")
    or _safe_include("noctria_gui.routes.observability_latency", "obs_bp")
)
if included:
    logger.info("Included router: noctria_gui.routes.observability_latency (any attr)")
else:
    logger.warning("Observability latency router not mounted (router/bp_obs_latency/obs_bp not found or incompatible)")

# 統治ルール可視化
_safe_include("noctria_gui.routes.governance_rules")

logger.info("✅ All available routers integrated. HAS_DASHBOARD=%s", HAS_DASHBOARD)

# ---------------------------------------------------------------------------
# Routes (root / favicon / toast-clear / health / exception handler)
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/dashboard" if HAS_DASHBOARD else "/pdca/summary")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = NOCTRIA_GUI_STATIC_DIR / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path, media_type="image/x-icon")
    return Response(status_code=204)

@app.get("/__clear_toast", include_in_schema=False)
async def __clear_toast(request: Request):
    try:
        if request.session.get("toast"):
            request.session.pop("toast", None)
    except Exception:
        pass
    return Response(status_code=204)

@app.get("/healthz", include_in_schema=False)
async def healthz():
    db_ok, db_msg = (False, "pdca summary not available")
    dsn_preview = _SUMMARY_DSN
    if _SUMMARY_AVAILABLE:
        try:
            db_ok, db_msg = _P.healthcheck()
        except Exception as e:
            db_ok, db_msg = False, f"healthcheck failed: {type(e).__name__}: {e!r}"

    return JSONResponse(
        {
            "ok": True,
            "static_dir": str(NOCTRIA_GUI_STATIC_DIR),
            "templates_dir": str(_tpl_dir),
            "has_dashboard": HAS_DASHBOARD,
            "session_enabled": True,
            "version": getattr(app, "version", "unknown"),
            "pdca_summary": {
                "available": _SUMMARY_AVAILABLE,
                "db_ok": db_ok,
                "message": db_msg,
                "dsn": dsn_preview,
            },
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Unhandled exception on %s %s: %s\nTraceback:\n%s", request.method, request.url, exc, tb)
    return JSONResponse(status_code=500, content={"detail": "サーバー内部エラーが発生しました。管理者にお問い合わせください。"})

# ---------------------------------------------------------------------------
# Local dev (optional)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("GUI_PORT", "8001"))
    reload_flag = os.getenv("UVICORN_RELOAD", "0").lower() in ("1", "true", "on")
    uvicorn.run("noctria_gui.main:app", host="0.0.0.0", port=port, reload=reload_flag)
