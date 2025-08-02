#!/usr/bin/env python3
# coding: utf-8

import sys
import os
import json
import logging
import traceback
from typing import Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response, RedirectResponse, JSONResponse, HTMLResponse
from starlette.responses import FileResponse

# もしsrcをPYTHONPATHに入れていない場合に対応する簡易設定（実行環境によって調整ください）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from src.core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ─────────────────────────────
# 📝 ロギング設定
# ─────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────
# 🚀 FastAPI 初期化
# ─────────────────────────────
app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="2.0.0",
)

# ─────────────────────────────
# 🗂️ 静的ファイルとテンプレート
# ─────────────────────────────
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# Jinja2カスタムフィルター例
def from_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}

templates.env.filters["from_json"] = from_json

# ─────────────────────────────
# 🔗 ルーター登録（既存のNoctria Kingdom各ルーター群）
# ─────────────────────────────
from noctria_gui.routes import (
    dashboard, home_routes, king_routes, logs_routes,
    path_checker, trigger, upload, upload_history,
    act_history, act_history_detail,
    pdca, pdca_recheck, pdca_routes, pdca_summary,
    prometheus_routes, push, push_history,
    statistics, statistics_detail, statistics_ranking,
    statistics_scoreboard, statistics_tag_ranking, statistics_compare,
    strategy_detail, strategy_heatmap, strategy_routes,
    tag_heatmap, tag_summary, tag_summary_detail,
    hermes, ai_routes,
    chat_history_api,  # ★ここにチャット履歴APIを追加
    chat_api           # ★チャットAPI（あれば）も追加
)

logger.info("Integrating all routers into the main application...")

# --- 既存ルーター群をinclude ---
app.include_router(home_routes.router)
app.include_router(dashboard.router)
app.include_router(king_routes.router)
app.include_router(trigger.router)
app.include_router(hermes.router)

app.include_router(act_history.router)
app.include_router(act_history_detail.router)
app.include_router(logs_routes.router)
app.include_router(upload_history.router)

app.include_router(pdca.router)
app.include_router(pdca_recheck.router)
app.include_router(pdca_routes.router)
app.include_router(pdca_summary.router)
app.include_router(push.router)
app.include_router(push_history.router)

app.include_router(strategy_routes.router, prefix="/strategies", tags=["strategies"])
app.include_router(strategy_detail.router)
app.include_router(strategy_heatmap.router)

app.include_router(statistics.router, prefix="/statistics", tags=["statistics"])
app.include_router(statistics_detail.router)
app.include_router(statistics_ranking.router)
app.include_router(statistics_scoreboard.router)
app.include_router(statistics_tag_ranking.router)
app.include_router(statistics_compare.router)

app.include_router(tag_summary.router)
app.include_router(tag_summary_detail.router)
app.include_router(tag_heatmap.router)

app.include_router(ai_routes.router)

app.include_router(path_checker.router)
app.include_router(prometheus_routes.router)
app.include_router(upload.router)

# --- ここから追加部分：チャット関連エンドポイント ---
app.include_router(chat_history_api.router)
app.include_router(chat_api.router)

logger.info("✅ All routers have been integrated successfully.")

# ─────────────────────────────
# 🏰 トップページは /dashboard へリダイレクト
# ─────────────────────────────
@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/dashboard")

# ─────────────────────────────
# 🖼 favicon.ico 対応
# ─────────────────────────────
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = NOCTRIA_GUI_STATIC_DIR / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path, media_type="image/x-icon")
    return Response(status_code=204)

# ─────────────────────────────
# 🌎 グローバル例外ハンドラー（オプション）
# ─────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled exception: {exc}\nTraceback:\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": "サーバー内部エラーが発生しました。管理者にお問い合わせください。"}
    )
