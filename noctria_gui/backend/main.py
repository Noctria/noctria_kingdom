#!/usr/bin/env python3
# coding: utf-8

import sys
from pathlib import Path

# ───────────────────────────────────────────────────────────
# 1) プロジェクトルート（noctria_kingdom）を sys.path に追加
# ───────────────────────────────────────────────────────────
# __file__ は main.py のファイルパスです。親ディレクトリから noctria_kingdom を参照します。
project_root = Path(__file__).resolve().parents[2]  # noctria_kingdom へのパス
src_dir = project_root / "src"  # src/ ディレクトリを設定

# src ディレクトリを sys.path に追加（これにより src/core や src/noctria_gui がインポート可能に）
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# これで src/core や src/noctria_gui をインポートできるようになります
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR
import noctria_gui.routes

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Any
import json

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
# 🔀 ルートハンドラー
# ========================================
@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """
    ルートアクセス時は /dashboard にリダイレクト
    """
    return RedirectResponse(url="/dashboard")

@app.get("/main", include_in_schema=False)
async def main_alias() -> RedirectResponse:
    """
    /main へのアクセスも /dashboard にリダイレクト
    """
    return RedirectResponse(url="/dashboard")


# ========================================
# 🔁 ルーターの自動登録
# ========================================
routers = getattr(routes_pkg, "routers", None)
if routers is not None and isinstance(routers, (list, tuple)):
    for router in routers:
        app.include_router(router)
        print(f"🔗 router 統合: tags={getattr(router, 'tags', [])}")
else:
    print("⚠️ noctria_gui.routes に routers が定義されていません")
