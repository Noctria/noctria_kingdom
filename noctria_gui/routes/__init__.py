#!/usr/bin/env python3
# coding: utf-8

"""
📦 noctria_gui.routes
- 統治機能ルーターを自動的に収集・登録する王国の中枢統制ファイル
- routes/ 以下の各モジュールから `router` を自動で拾います
"""

import sys
import importlib
import pkgutil
import traceback
from pathlib import Path
from fastapi import APIRouter
from typing import List

# ───────────────────────────────────────────────
# 🛠️ モジュール検索パスに src/ を明示追加
# ───────────────────────────────────────────────
src_dir = Path(__file__).resolve().parents[2] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# ✅ 収集されたルーターを保持
routers: List[APIRouter] = []

# ✅ 自身のパスをルート探索用にセット
__path__ = __path__  # required for pkgutil.iter_modules

# ========================================
# 🔍 統治ルーター探索処理（自動登録）
# ========================================
for finder, module_name, ispkg in pkgutil.iter_modules(__path__):
    if module_name.startswith("_"):
        continue  # __init__.py や _hidden.py などはスキップ

    full_module_name = f"{__name__}.{module_name}"
    try:
        module = importlib.import_module(full_module_name)
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            routers.append(router)
            print(f"✅ Loaded router from {full_module_name}")
        else:
            print(f"⚠️  No router found in {full_module_name}")
    except Exception:
        print(f"❌ Failed to load router from {full_module_name}")
        traceback.print_exc()
