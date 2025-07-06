#!/usr/bin/env python3
# coding: utf-8

"""
📦 noctria_gui.routes
- routes/ 以下の *.py モジュールから router を自動収集する
"""

import importlib
import pkgutil

# すべての router を格納するリスト
routers = []

# このパッケージのパスを取得（必要：__init__.py 実行時に __path__ が初期化される）
__path__ = __path__  # required for pkgutil to work correctly

# 🔄 自動インポート処理
for finder, module_name, ispkg in pkgutil.iter_modules(__path__):
    if module_name.startswith("_"):
        continue  # __init__.py や非公開モジュールは除外

    try:
        mod = importlib.import_module(f"{__name__}.{module_name}")
        if hasattr(mod, "router"):
            routers.append(mod.router)
            print(f"✅ router 読込: {module_name}")
        else:
            print(f"⚠️ router 未定義: {module_name}")
    except Exception as e:
        print(f"❌ ルーターインポート失敗: {module_name} - {e}")
