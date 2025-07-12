#!/usr/bin/env python3
# coding: utf-8

"""
🌐 Noctria Kingdom GUI 起動スクリプト（自動ルート登録版）
- FastAPIで王国の統治パネルを展開
- routes/ 以下の全ルートを自動登録
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Any
import json

# ✅ 統治下の正式パス（core/path_config.pyに定義済み）
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ✅ GUIルートモジュール（__init__.pyで routers 一覧を構築）
import noctria_gui.routes as routes_pkg

# ========================================
# 🚀 FastAPI GUI アプリケーション構成
# ========================================

app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.0.0",
)

# ✅ 静的ファイルとテンプレートの登録
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ✅ Jinja2 カスタムフィルタ：from_json（文字列 → dict）
def from_json(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return {}

templates.env.filters["from_json"] = from_json

# ✅ テンプレート環境を app.state に格納（共通アクセス用）
app.state.templates = templates  # FastAPIの慣習的保存方法

# ========================================
# 🔁 ルーターの自動登録
# ========================================

routers = getattr(routes_pkg, "routers", None)
if routers is not None and isinstance(routers, (list, tuple)):
    for router in routers:
        app.include_router(router)
        print(f"🔗 router 統合: {getattr(router, 'tags', [])}")
else:
    print("⚠️ noctria_gui.routes に routers が定義されていません")
