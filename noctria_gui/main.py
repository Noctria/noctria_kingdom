#!/usr/bin/env python3
# coding: utf-8

import json
import sys
import logging
from typing import Any
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response
from starlette.responses import FileResponse

from src.core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ─────────────────────────────────────────────
# 📝 ロギング設定
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🚀 FastAPI 初期化
# ─────────────────────────────────────────────
app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="2.0.0",
)

# ─────────────────────────────────────────────
# 🗂️ 静的ファイルとテンプレート
# ─────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def from_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}

templates.env.filters["from_json"] = from_json

# ─────────────────────────────────────────────
# 🔗 ルーター登録
# ─────────────────────────────────────────────
from noctria_gui.routes import (
    dashboard, home_routes, king_routes, logs_routes,
    path_checker, trigger, upload, upload_history,
    act_history, act_history_detail,
    pdca, pdca_recheck, pdca_routes, pdca_summary,
    prometheus_routes, push,
    statistics_detail, statistics_ranking,
    statistics_scoreboard, statistics_tag_ranking, statistics_compare,
    strategy_detail, strategy_heatmap, strategy_routes,
    tag_heatmap, tag_summary, tag_summary_detail
)

logger.info("Integrating all routers into the main application...")

# --- メイン機能 ---
app.include_router(home_routes.router)
app.include_router(dashboard.router)
app.include_router(king_routes.router)
app.include_router(trigger.router)

# --- ログ・履歴 ---
app.include_router(act_history.router)
app.include_router(act_history_detail.router)
app.include_router(logs_routes.router)
app.include_router(upload_history.router)

# --- PDCA関連 ---
app.include_router(pdca.router)
app.include_router(pdca_recheck.router)
app.include_router(pdca_routes.router)
app.include_router(pdca_summary.router)
app.include_router(push.router)

# --- 戦略 ---
app.include_router(strategy_routes.router, prefix="/strategies", tags=["strategies"])
app.include_router(strategy_detail.router)
app.include_router(strategy_heatmap.router)

# --- 統計（明示的に statistics_dashboard は除外）---
app.include_router(statistics_detail.router)
app.include_router(statistics_ranking.router)
app.include_router(statistics_scoreboard.router)
app.include_router(statistics_tag_ranking.router)
app.include_router(statistics_compare.router)
app.include_router(tag_summary.router)
app.include_router(tag_summary_detail.router)
app.include_router(tag_heatmap.router)

# --- その他 ---
app.include_router(path_checker.router)
app.include_router(prometheus_routes.router)
app.include_router(upload.router)

logger.info("✅ All routers have been integrated successfully.")

# ─────────────────────────────────────────────
# 🖼 favicon.ico対策（404抑止）
# ─────────────────────────────────────────────
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = NOCTRIA_GUI_STATIC_DIR / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path, media_type="image/x-icon")
    return Response(status_code=204)
