#!/usr/bin/env python3
# coding: utf-8

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json  # ✅ JSONフィルター用に追加

# ✅ Noctria Kingdom の統治下にある正式パス管理
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR

# ✅ ルート定義（各画面モジュール）
from noctria_gui.routes import home_routes, strategy_routes
from noctria_gui.routes import pdca, upload  # ✅ PDCA + アップロード用ルーティングを追加

# ========================================
# 🌐 FastAPI GUI 起動構成（Noctria Kingdom）
# ========================================

app = FastAPI(
    title="Noctria Kingdom GUI",
    description="王国の中枢制御パネル（DAG起動・戦略管理・評価表示など）",
    version="1.0.0",
)

# ✅ 静的ファイル & テンプレートの登録
app.mount("/static", StaticFiles(directory=str(NOCTRIA_GUI_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ✅ Jinja2フィルター登録（from_json で JSON→dict にパース可能に）
templates.env.filters["from_json"] = lambda x: json.loads(x)

# ✅ ルータ登録（責務ごとに登録）
app.include_router(home_routes.router)
app.include_router(strategy_routes.router)
app.include_router(pdca.router)     # 🔁 PDCA実行・履歴タブ
app.include_router(upload.router)   # 🆙 戦略アップロード機能
