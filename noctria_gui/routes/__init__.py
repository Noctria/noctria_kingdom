#!/usr/bin/env python3
# coding: utf-8

"""
📦 noctria_gui.routes
- 統治機能ルーターを自動的に収集・登録する王国の中枢統制ファイル
- routes/ 以下の各モジュールから `router` を自動で拾います
"""

import importlib
import pkgutil
from fastapi import APIRouter
from typing import List

# ✅ router 一覧（FastAPI本体に登録されるルーター群）
routers: List[APIRouter] = []

# ✅ この __init__.py 自身の __path__ を起点にサブモジュールを探索
__path__ = __path__  # pkgutil.iter_modules のために必要

# 🔍 統治ルーター探索処理
for finder, module_name, ispkg in pkgutil.iter_modules(__path__):
    if module_name.startswith("_"):
        continue  # __init__.py や _private.py などは除外
    full_module_name = f"{__name__}.{module_name}"
    module = importlib.import_module(full_module_name)
    # 各モジュールが `router: APIRouter` を持っていれば登録
    router = getattr(module, "router", None)
    if isinstance(router, APIRouter):
        routers.append(router)
        print(f"🔍 loaded router from {full_module_name}")
