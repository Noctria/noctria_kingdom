#!/usr/bin/env python3
# coding: utf-8

"""
🌐 Noctria Kingdom GUI 起動スクリプト（自動ルート登録版）
- FastAPI で routes/ 以下の全ルートを自動登録
- ルート ("/") は /dashboard にリダイレクト
"""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Any
import json

# path_config で定義済みのディレクトリ
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# 自動登録対象の routers リスト
import noctria_gui.routes as routes_pkg

app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.0.0",
)

# 静的ファイルマウント
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")

# Jinja2 テンプレート設定
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# カスタムフィルタ：JSON文字列→dict
def from_json(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return {}

templates.env.filters["from_json"] = from_json
app.state.templates = templates

# ───────────
# ルート設定
# ───────────
@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")

@app.get("/main", include_in_schema=False)
async def main_alias() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")

# ───────────
# ルーター自動登録
# ───────────
routers = getattr(routes_pkg, "routers", None)
if isinstance(routers, list):
    for router in routers:
        app.include_router(router)
        print(f"🔗 router 統合: {getattr(router, 'prefix', 'no-prefix')}")
else:
    print("⚠️ noctria_gui.routes.routers が見つかりませんでした")
