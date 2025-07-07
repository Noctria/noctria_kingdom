#!/usr/bin/env python3
# coding: utf-8

"""
🌐 Noctria Kingdom GUI 起動スクリプト（自動ルート登録版）
- FastAPIにより王国の統治パネルを展開
- routes/ 以下の全ルートを自動登録
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
from typing import Any

# ✅ 統治下の正式パス
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ✅ GUIルートモジュール（__init__.pyで router 一覧を構築）
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
app.state.templates: Jinja2Templates = templates

# ========================================
# 🔁 ルーターの自動登録（__init__.py内で構築された routers を利用）
# ========================================

if hasattr(routes_pkg, "routers"):
    for router in routes_pkg.routers:
        app.include_router(router)
        print(f"🔗 router 統合: {router.tags}")
else:
    print("⚠️ noctria_gui.routes に routers が定義されていません")
