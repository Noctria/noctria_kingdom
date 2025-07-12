#!/usr/bin/env python3
# coding: utf-8

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import json
from typing import Any

# プロジェクトのコアモジュールとルーターをインポート
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR
from noctria_gui.routes import (
    dashboard, 
    act_history,
    act_history_detail,
    pdca_routes, # エラーが発生していたPDCAルートを追加
    strategy_routes,
    # ... 他に必要なルーターをここに追加 ...
)


# ========================================
# 🚀 FastAPI GUI アプリケーション構成
# ========================================
app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.1.0",
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
# 各機能のルーターをアプリケーションに登録します
app.include_router(dashboard.router)
app.include_router(act_history.router)
app.include_router(act_history_detail.router)
app.include_router(pdca_routes.router) # PDCAルーターを登録
app.include_router(strategy_routes.router)
# ... 他のルーターも同様に登録 ...

print("✅ All routers have been integrated.")


# ========================================
# 🔀 ルートハンドラー (トップページリダイレクト)
# ========================================
@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """
    ルートアクセス時は /dashboard にリダイレクトします。
    """
    return RedirectResponse(url="/dashboard")

