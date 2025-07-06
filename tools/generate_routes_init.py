#!/usr/bin/env python3
# coding: utf-8

"""
🛠 __init__.py 自動生成スクリプト
- noctria_gui/routes 以下の *.py モジュールから router を収集し、
  __init__.py を構築して routers[] に登録する構成を生成
"""

import os
from pathlib import Path

# 📌 固定パス（調整する場合は core.path_config 等へ移行しても可）
ROUTES_DIR = Path("noctria_gui/routes")
INIT_FILE = ROUTES_DIR / "__init__.py"

HEADER = '''#!/usr/bin/env python3
# coding: utf-8

"""
📦 noctria_gui.routes
- routes/ 以下の *.py モジュールから router を自動収集する
"""

import importlib
import pkgutil

# すべての router を格納するリスト
routers = []

# このパッケージのパスを取得
__path__ = __path__  # required for pkgutil
'''

MAIN_LOOP = '''
# 自動インポート処理
for _, module_name, _ in pkgutil.iter_modules(__path__):
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
'''

def generate_init():
    content = HEADER + MAIN_LOOP
    try:
        with open(INIT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ __init__.py を更新しました: {INIT_FILE}")
    except Exception as e:
        print(f"❌ __init__.py 書き込み失敗: {e}")

if __name__ == "__main__":
    generate_init()
