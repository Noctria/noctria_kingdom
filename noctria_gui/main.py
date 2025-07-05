#!/usr/bin/env python3
# coding: utf-8

"""
🌐 Noctria Kingdom GUI 起動構成
- 統治パネル（戦略・評価・PDCA・ログなど）を統括
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json  # ✅ for from_json filter

# ✅ 統一パス定義（Noctria Kingdom 標準）
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ✅ 各画面ルートのインポート
from noctria_gui.routes import (
    home_routes,
    strategy_routes,
    pdca,
    upload,
    upload_history,
    statistics,
    act_history,
    push_history,
    logs_routes,  # ✅ 統治ログ出力ルートを追加
)

# ===============================
# 🌐 GUI アプリケーション定義
# ===============================

app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.0.0",
)

# ✅ 静的ファイルとテンプレートの登録
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ✅ カスタムフィルター定義（Jinja2用）
def from_json(value):
    try:
        return json.loads(value)
    except Exception:
        return {}

templates.env.filters["from_json"] = from_json
app.state.templates = templates  # ✅ 他モジュールでも参照可

# ===============================
# ✅ 各画面ルーターの登録
# ===============================
app.include_router(home_routes.router)
app.include_router(strategy_routes.router)
app.include_router(pdca.router)
app.include_router(upload.router)
app.include_router(upload_history.router)
app.include_router(statistics.router)
app.include_router(act_history.router)
app.include_router(push_history.router)
app.include_router(logs_routes.router)  # ✅ 統治ログ出力ボタン用
