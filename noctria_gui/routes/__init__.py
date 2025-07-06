#!/usr/bin/env python3
# coding: utf-8

"""
📦 noctria_gui.routes
- routes/ 以下の *.py モジュールから router を自動収集する
- 📌 このファイルは自動生成されました。手動編集は上書きされます。
"""

import importlib
import pkgutil
from fastapi import APIRouter
from typing import List

# ✅ router 一覧（FastAPI用）
routers: List[APIRouter] = []

# ✅ この __init__.py の __path__ がモジュール探索の起点になる
__path__ = __path__  # required for pkgutil.iter_modules to work correctly

# 🔄 自動インポート処理（routes/ 以下の各 .py にある router を自動登録）
for finder, module_name, ispkg in pkgutil.iter_modules(__path__):
    if module_name.startswith("_"):
        continue  # __init__.py や _private.py はスキップ

    try:
        # モジュールインポート
        mod = importlib.import_module(f"{__name__}.{module_name}")

        # router を含むモジュールのみ登録
        if hasattr(mod, "router"):
            routers.append(mod.router)
            print(f"[routes] ✅ router 読込成功: {module_name}")
        else:
            print(f"[routes] ⚠️ router 未定義: {module_name}")

    except Exception as e:
        print(f"[routes] ❌ ルーターインポート失敗: {module_name} - {repr(e)}")
