#!/usr/bin/env python3
# coding: utf-8

"""
🌐 Noctria Kingdom GUI 起動スクリプト（自動ルート登録対応版）
- FastAPIにより王国の統治パネルを展開
- `noctria_gui.routes/` 配下の全ルートを自動検出・登録
"""

import json
import importlib
import pkgutil
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

# ✅ 統治下の正式パス
from core.path_config import NOCTRIA_GUI_STATIC_DIR, NOCTRIA_GUI_TEMPLATES_DIR
import noctria_gui.routes  # ルート自動探索用

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
def from_json(value: str):
    try:
        return json.loads(value)
    except Exception:
        return {}

templates.env.filters["from_json"] = from_json

# ✅ テンプレート環境を app.state に格納（共通アクセス用）
app.state.templates = templates

# ========================================
# 🔁 ルート自動登録（routes/*.py を動的に include）
# ========================================
routes_package = noctria_gui.routes
package_path = Path(routes_package.__file__).parent

for _, module_name, is_pkg in pkgutil.iter_modules([str(package_path)]):
    if is_pkg or module_name.startswith("_"):
        continue  # サブパッケージや __init__ は除外
    try:
        full_module_name = f"{routes_package.__name__}.{module_name}"
        module = importlib.import_module(full_module_name)
        if hasattr(module, "router"):
            app.include_router(module.router)
            print(f"✅ ルート登録: {full_module_name}")
    except Exception as e:
        print(f"⚠️ ルート登録失敗: {module_name} - {e}")
