#!/usr/bin/env python3
# coding: utf-8

"""
📦 noctria_gui.routes
- 統治機能ルーターを自動的に収集・登録する王国の中枢統制ファイル
- 📌 自動生成構成（手動編集は次回生成で上書きされる可能性あり）
"""

import importlib
import pkgutil
from fastapi import APIRouter
from typing import List

# ✅ router 一覧（FastAPI本体に登録されるルーター群）
routers: List[APIRouter] = []

# ✅ この __init__.py 自身の __path__ を起点にサブモジュールを探索
__path__ = __path__  # required for pkgutil.iter_modules to function

# ========================================
# 🔍 統治ルーター探索処理
# ========================================
for finder, module_name, ispkg in pkgutil.iter_modules(__path__):
    if module_name.startswith("_"):
        continue  # __init__.py や _hidden.py などはスキップ

    try:
        # 📥 モジュールインポート
        module_fullname = f"{__name__}.{module_name}"
        mod = importlib.import_module(module_fullname)

        # ✅ router 属性を持つモジュールのみ登録
        if hasattr(mod, "router") and isinstance(mod.router, APIRouter):
            routers.append(mod.router)
            print(f"[routes_loader] ✅ ルーター読込成功: {module_name}")
        else:
            print(f"[routes_loader] ⚠️ router 不在または形式不正: {module_name}")

    except Exception as e:
        print(f"[routes_loader] ❌ インポート失敗: {module_name} - {repr(e)}")
