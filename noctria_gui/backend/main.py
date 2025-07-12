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
# 修正点: 全てのルーターをインポート
# ========================================
# routesディレクトリ内の各機能（ページ）のロジックを読み込みます
from noctria_gui.routes import (
    dashboard, 
    act_history,
    act_history_detail,
    home_routes,
    king_routes,
    logs_routes,
    pdca_routes,
    prometheus_routes,
    push,
    statistics,
    strategy_routes,
    upload,
    # 必要に応じて他のルーターもここに追加します
    # 例: strategy_compare, statistics_dashboard など
)


# ========================================
# 🚀 FastAPI GUI アプリケーション構成
# ========================================
app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.2.0",
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
# 🔁 ルーターの自動登録
# ========================================
# 読み込んだ各機能のルーターをアプリケーションに登録します
print("Integrating routers...")
app.include_router(dashboard.router, prefix="", tags=["Core"])
app.include_router(home_routes.router, prefix="", tags=["Core"])

# 各機能ページのルーター
app.include_router(act_history.router)
app.include_router(act_history_detail.router)
app.include_router(king_routes.router)
app.include_router(logs_routes.router)
app.include_router(pdca_routes.router)
app.include_router(prometheus_routes.router)
app.include_router(push.router)
app.include_router(statistics.router)
app.include_router(strategy_routes.router)
app.include_router(upload.router)

print("✅ All routers have been integrated successfully.")


# ========================================
# 🔀 ルートハンドラー (トップページリダイレクト)
# ========================================
# @app.get("/", include_in_schema=False)
# async def root() -> RedirectResponse:
#     """
#     ルートアクセス時は /dashboard にリダイレクトします。
#     home_routesで処理されるため、通常は不要です。
#     """
#     return RedirectResponse(url="/dashboard")

