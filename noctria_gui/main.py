#!/usr/bin/env python3
# coding: utf-8

"""
🌐 Noctria Kingdom GUI 起動スクリプト
- FastAPIにより王国の統治パネルを展開
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json  # ✅ for from_json filter

# ✅ 統治下の正式パス
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ✅ 各ルートモジュールの導入
from noctria_gui.routes import (
    home_routes,
    strategy_routes,
    strategy_detail,
    strategy_compare,         # ✅ 戦略比較ルート
    tag_summary,
    tag_summary_detail,
    statistics,
    act_history,
    push_history,
    logs_routes,
    upload,
    upload_history,
    pdca,
)

# ========================================
# 🚀 FastAPI GUI 構成（Noctria Kingdom）
# ========================================

app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.0.0",
)

# ✅ 静的ファイル＆テンプレート設定
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ✅ Jinja2 カスタムフィルタ（dict → JSON）
def from_json(value):
    try:
        return json.loads(value)
    except Exception:
        return {}

templates.env.filters["from_json"] = from_json

# ✅ templates を状態に保持（グローバル参照用）
app.state.templates = templates

# ✅ 全ルートを統治パネルへ結集
app.include_router(home_routes.router)
app.include_router(strategy_routes.router)
app.include_router(strategy_detail.router)
app.include_router(strategy_compare.router)       # ✅ 比較系ルート
app.include_router(tag_summary.router)
app.include_router(tag_summary_detail.router)
app.include_router(statistics.router)
app.include_router(act_history.router)
app.include_router(push_history.router)
app.include_router(logs_routes.router)
app.include_router(upload.router)
app.include_router(upload_history.router)
app.include_router(pdca.router)
