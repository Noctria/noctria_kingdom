#!/usr/bin/env python3
# coding: utf-8

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import json
from typing import Any

# --- プロジェクトのコアモジュール ---
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ========================================
# 🚀 FastAPI GUI アプリケーション構成
# ========================================
app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.4.0",
)

# ✅ 静的ファイルとテンプレートの登録
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ✅ Jinja2 カスタムフィルタ (アプリケーション全体で利用可能)
def from_json(value: str) -> Any:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
templates.env.filters["from_json"] = from_json

# ========================================
# ルーターのインポート
# ========================================
from noctria_gui.routes import (
    dashboard, 
    home_routes,
    act_history,
    act_history_detail,
    king_routes,
    logs_routes,
    path_checker,
    pdca,
    pdca_recheck,
    pdca_routes,
    prometheus_routes,
    push,
    statistics,
    statistics_compare,
    statistics_detail,
    statistics_ranking,
    statistics_scoreboard,
    statistics_tag_ranking,
    statistics_dashboard,  # ← ✅ 追加ここ！
    strategy_compare,
    strategy_detail,
    strategy_heatmap,
    strategy_routes,
    tag_heatmap,
    tag_summary,
    upload,
    upload_history,
)

# ========================================
# 🔁 ルーター登録
# ========================================
print("Integrating all routers into the main application...")

# プレフィックスが異なるものを先に登録
app.include_router(dashboard.router)
app.include_router(home_routes.router)

# 各機能ページのルーター
app.include_router(act_history.router)
app.include_router(act_history_detail.router)
app.include_router(king_routes.router)
app.include_router(logs_routes.router)
app.include_router(path_checker.router)
app.include_router(pdca.router)
app.include_router(pdca_recheck.router)
app.include_router(pdca_routes.router)
app.include_router(prometheus_routes.router)
app.include_router(push.router)
app.include_router(statistics.router)
app.include_router(statistics_compare.router)
app.include_router(statistics_detail.router)
app.include_router(statistics_ranking.router)
app.include_router(statistics_scoreboard.router)
app.include_router(statistics_tag_ranking.router)
app.include_router(statistics_dashboard.router)  # ← ✅ 追加ここ！
app.include_router(strategy_compare.router)
app.include_router(strategy_detail.router)
app.include_router(strategy_heatmap.router)
app.include_router(strategy_routes.router)
app.include_router(tag_heatmap.router)
app.include_router(tag_summary.router)
app.include_router(upload.router)
app.include_router(upload_history.router)

print("✅ All routers have been integrated successfully.")

# ========================================
# 🔀 トップページリダイレクト（必要なければ無効化）
# ========================================
# @app.get("/", include_in_schema=False)
# async def root() -> RedirectResponse:
#     return RedirectResponse(url="/dashboard")
