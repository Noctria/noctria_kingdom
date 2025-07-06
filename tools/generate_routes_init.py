#!/usr/bin/env python3
# coding: utf-8

"""
🛠 __init__.py 自動生成スクリプト（Noctria Kingdom）
- noctria_gui/routes/ 以下の *.py ファイルを検出し、明示的な import 文を記述
- FastAPI main.py の動的 include_router に対応しつつ、IDE補完と整合性を維持
"""

import os
from pathlib import Path

# 📍 ルートディレクトリ推定（このスクリプトが tools/ 以下にある前提）
CURRENT_DIR = Path(__file__).resolve().parent
ROUTES_DIR = CURRENT_DIR.parent / "noctria_gui" / "routes"
INIT_FILE = ROUTES_DIR / "__init__.py"

def generate_routes_init():
    """📦 routes/__init__.py を自動生成する"""
    module_lines = []
    
    for py_file in sorted(ROUTES_DIR.glob("*.py")):
        name = py_file.stem
        if name.startswith("_") or name == "__init__":
            continue
        module_lines.append(f"from . import {name}")

    banner = "# 📦 このファイルは自動生成されました。手動編集は上書きされます。\n\n"
    content = banner + "\n".join(module_lines) + "\n"

    try:
        with open(INIT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ __init__.py を更新しました: {INIT_FILE}")
    except Exception as e:
        print(f"❌ 書き込み失敗: {e}")

if __name__ == "__main__":
    generate_routes_init()
