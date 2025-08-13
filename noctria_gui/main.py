#!/usr/bin/env python3
# coding: utf-8
"""
Noctria Kingdom GUI - main entrypoint
- ルーター統合
- 静的/テンプレートの安全マウント
- 例外ハンドラ
"""

from __future__ import annotations

import os
import sys
import json
import logging
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response, RedirectResponse, JSONResponse
from starlette.responses import FileResponse

# -----------------------------------------------------------------------------
# import path: <repo_root>/src を最優先に追加
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# path_config（集中管理）
from src.core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR  # type: ignore

# -----------------------------------------------------------------------------
# logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("noctria_gui.main")

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="2.0.1",
)

# -----------------------------------------------------------------------------
# 静的/テンプレートの安全マウント（存在しない場合も落ちないように）
# -----------------------------------------------------------------------------
# /static
if NOCTRIA_GUI_STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(NOTRIA_GUI_STATIC_DIR)), name="static")
    logger.info(f"Static mounted: {NOCTRIA_GUI_STATIC_DIR}")
else:
    logger.warning(f"Static dir not found: {NOCTRIA_GUI_STATIC_DIR} (skip mounting)")

# templates（存在しない場合はフォールバックを試みる）
_tpl_dir = NOCTRIA_GUI_TEMPLATES_DIR if NOCTRIA_GUI_TEMPLATES_DIR.exists() else (PROJECT_ROOT / "noctria_gui" / "templates")
templates = Jinja2Templates(directory=str(_tpl_dir))
logger.info(f"Templates dir: {_tpl_dir}")

def from_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}

templates.env.filters["from_json"] = from_json

# -----------------------------------------------------------------------------
# ルーターの取り込み
# 必要に応じて存在しないモジュールはスキップ（開発中の崩壊を防ぐ）
# -----------------------------------------------------------------------------
def _safe_include(module_path: str, attr: str = "router", *, prefix: str | None = None, tags: list[str] | None = None):
    try:
        mod = __import__(module_path, fromlist=[attr])
        router = getattr(mod, attr)
        if prefix or tags:
            app.include_router(router, prefix=prefix or "", tags=tags or [])
        else:
            app.include_router(router)
        logger.info(f"Included router: {module_path}")
    except Exception as e:
        logger.warning(f"Skip router '{module_path}': {e}")

logger.info("Integrating routers...")

# 主要ルーター郡（存在しなくてもスキップ可）
_safe_include("noctria_gui.routes.home_routes")
_safe_include("noctria_gui.routes.dashboard")
_safe_include("noctria_gui.routes.king_routes")
_safe_include("noctria_gui.routes.trigger")
_safe_include("noctria_gui.routes.hermes")

_safe_include("noctria_gui.routes.act_history")
_safe_include("noctria_gui.routes.act_history_detail")
_safe_include("noctria_gui.routes.logs_routes")
_safe_include("noctria_gui.routes.upload_history")

_safe_include("noctria_gui.routes.pdca")
_safe_include("noctria_gui.routes.pdca_recheck")
_safe_include("noctria_gui.routes.pdca_routes")
_safe_include("noctria_gui.routes.pdca_summary")

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

_safe_include("noctria_gui.routes.ai_routes")
_safe_include("noctria_gui.routes.devcycle_history")

_safe_include("noctria_gui.routes.path_checker")
_safe_include("noctria_gui.routes.prometheus_routes")
_safe_include("noctria_gui.routes.upload")

_safe_include("noctria_gui.routes.chat_history_api")
# _safe_include("noctria_gui.routes.chat_api")  # APIキー未設定環境での誤爆防止

# ★ 新規: PDCA 可観測性ビュー（/pdca/timeline, /pdca/latency/daily 等）
_safe_include("noctria_gui.routes.observability")

logger.info("✅ All available routers integrated.")

# -----------------------------------------------------------------------------
# Routes (root / favicon / health / exception handler)
# -----------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root_redirect():
    # ダッシュボードが無い環境では PDCA タイムラインへ
    try:
        return RedirectResponse(url="/dashboard")
    except Exception:
        return RedirectResponse(url="/pdca/timeline")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = NOCTRIA_GUI_STATIC_DIR / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path, media_type="image/x-icon")
    return Response(status_code=204)

@app.get("/healthz", include_in_schema=False)
async def healthz():
    return JSONResponse({"ok": True})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Unhandled exception: %s\nTraceback:\n%s", exc, tb)
    return JSONResponse(
        status_code=500,
        content={"detail": "サーバー内部エラーが発生しました。管理者にお問い合わせください。"},
    )
