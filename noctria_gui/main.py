# noctria_gui/main.py
#!/usr/bin/env python3
# coding: utf-8
"""
Noctria Kingdom GUI - main entrypoint

- ルーター統合（存在しないものは安全にスキップ）
- 静的/テンプレートの安全マウント
- 例外ハンドラ / healthz / ルートリダイレクト

今回のポイント
- path_config 不在時でもフォールバックして起動継続
- Jinja2 に from_json フィルタを登録
- HAS_DASHBOARD を柔軟に判定（module名に ".dashboard" を含む場合を許容）
- 統治ルール可視化ルーター（governance_rules）を配線
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from importlib import import_module
from pathlib import Path
from typing import Any, Optional, Sequence

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse

# -----------------------------------------------------------------------------
# import path: <repo_root>/src を最優先に追加
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # <repo_root>/noctria_gui/ -> parents[1] == <repo_root>
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# -----------------------------------------------------------------------------
# 集中管理パス設定（path_config が無くても動くようにフォールバック）
# -----------------------------------------------------------------------------
# 既定のフォールバック
_FALLBACK_STATIC_DIR = PROJECT_ROOT / "noctria_gui" / "static"
_FALLBACK_TEMPLATES_DIR = PROJECT_ROOT / "noctria_gui" / "templates"

try:
    # 統一方針：src.* の絶対インポート
    from src.core.path_config import (  # type: ignore
        NOCTRIA_GUI_STATIC_DIR as _STATIC_DIR,
        NOCTRIA_GUI_TEMPLATES_DIR as _TEMPLATES_DIR,
    )
    NOCTRIA_GUI_STATIC_DIR: Path = Path(str(_STATIC_DIR))
    NOCTRIA_GUI_TEMPLATES_DIR: Path = Path(str(_TEMPLATES_DIR))
except Exception:
    # path_config が未整備でも落とさない
    NOCTRIA_GUI_STATIC_DIR = _FALLBACK_STATIC_DIR
    NOCTRIA_GUI_TEMPLATES_DIR = _FALLBACK_TEMPLATES_DIR

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
    version="2.3.0",
)

# -----------------------------------------------------------------------------
# 静的/テンプレートの安全マウント（存在しない場合も落ちないように）
# -----------------------------------------------------------------------------
# /static
if NOCTRIA_GUI_STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
    logger.info("Static mounted: %s", NOCTRIA_GUI_STATIC_DIR)
else:
    logger.warning("Static dir not found: %s (skip mounting)", NOCTRIA_GUI_STATIC_DIR)

# templates（存在しない場合はフォールバック）
_tpl_dir = NOCTRIA_GUI_TEMPLATES_DIR if NOCTRIA_GUI_TEMPLATES_DIR.exists() else _FALLBACK_TEMPLATES_DIR
templates = Jinja2Templates(directory=str(_tpl_dir))
logger.info("Templates dir: %s", _tpl_dir)

# 便利フィルタ
def from_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value

templates.env.filters["from_json"] = from_json

# -----------------------------------------------------------------------------
# ルーターの取り込み（存在しないモジュールはスキップ）
# -----------------------------------------------------------------------------
HAS_DASHBOARD = False

def _safe_include(
    module_path: str,
    attr: str = "router",
    *,
    prefix: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
) -> bool:
    """
    ルーターを安全に取り込み。成功/失敗を bool で返す。
    """
    global HAS_DASHBOARD
    try:
        mod = import_module(module_path)
        router = getattr(mod, attr)
        if prefix or tags:
            app.include_router(router, prefix=prefix or "", tags=list(tags or []))
        else:
            app.include_router(router)
        logger.info("Included router: %s", module_path)
        # ダッシュボード判定を少し緩める（例: routes.dashboard_v2 でも検出）
        if ".dashboard" in module_path:
            HAS_DASHBOARD = True
        return True
    except Exception as e:
        logger.warning("Skip router '%s': %s", module_path, e)
        return False

logger.info("Integrating routers...")

# 主要ルーター群（存在しなくてもスキップ可）
_safe_include("noctria_gui.routes.home_routes")
_safe_include("noctria_gui.routes.dashboard")            # ダッシュボード（あれば HAS_DASHBOARD=True）

# 王の統治系
_safe_include("noctria_gui.routes.king_routes")
_safe_include("noctria_gui.routes.trigger")
_safe_include("noctria_gui.routes.hermes")

# Act/ログ系
_safe_include("noctria_gui.routes.act_history")
_safe_include("noctria_gui.routes.act_history_detail")
_safe_include("noctria_gui.routes.logs_routes")
_safe_include("noctria_gui.routes.upload_history")

# --- PDCA関連 ---
_safe_include("noctria_gui.routes.pdca")                 # 既存：PDCAトップ/補助
_safe_include("noctria_gui.routes.pdca_recheck")         # /pdca/control, /pdca/recheck（環境により未配置可）
_safe_include("noctria_gui.routes.pdca_routes")          # /pdca-dashboard（HUDダッシュボード）
_safe_include("noctria_gui.routes.pdca_summary")         # /pdca/summary & /pdca/api/summary

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

# AI/DevCycle系
_safe_include("noctria_gui.routes.ai_routes")
_safe_include("noctria_gui.routes.devcycle_history")

# ユーティリティ
_safe_include("noctria_gui.routes.path_checker")
_safe_include("noctria_gui.routes.prometheus_routes")
_safe_include("noctria_gui.routes.upload")

# チャット履歴API（循環importの可能性があるため安全取り込み）
_safe_include("noctria_gui.routes.chat_history_api")
# _safe_include("noctria_gui.routes.chat_api")  # APIキー未設定環境での誤爆防止

# 可観測性ビュー
_safe_include("noctria_gui.routes.observability")

# 🔰 新規: 統治ルール可視化（metrics/timeline + HTML）
_safe_include("noctria_gui.routes.governance_rules")

logger.info("✅ All available routers integrated. HAS_DASHBOARD=%s", HAS_DASHBOARD)

# -----------------------------------------------------------------------------
# Routes (root / favicon / health / exception handler)
# -----------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root_redirect():
    # ダッシュボードが読み込めていれば /dashboard、なければ PDCA サマリーへ
    return RedirectResponse(url="/dashboard" if HAS_DASHBOARD else "/pdca/summary")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = NOCTRIA_GUI_STATIC_DIR / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path, media_type="image/x-icon")
    return Response(status_code=204)

@app.get("/healthz", include_in_schema=False)
async def healthz():
    return JSONResponse(
        {
            "ok": True,
            "static_dir": str(NOCTRIA_GUI_STATIC_DIR),
            "templates_dir": str(_tpl_dir),
            "has_dashboard": HAS_DASHBOARD,
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Unhandled exception on %s %s: %s\nTraceback:\n%s", request.method, request.url, exc, tb)
    return JSONResponse(
        status_code=500,
        content={"detail": "サーバー内部エラーが発生しました。管理者にお問い合わせください。"},
    )

# -----------------------------------------------------------------------------
# Local dev (optional)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("GUI_PORT", "8001"))
    reload_flag = os.getenv("UVICORN_RELOAD", "0").lower() in ("1", "true", "on")
    uvicorn.run("noctria_gui.main:app", host="0.0.0.0", port=port, reload=reload_flag)
