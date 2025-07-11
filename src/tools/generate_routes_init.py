#!/usr/bin/env python3
# coding: utf-8

"""
🛠 generate_routes_init.py
- noctria_gui.routes.__init__.py を自動生成し、すべての router を登録する
"""

import os
from pathlib import Path

ROUTES_DIR = Path(__file__).resolve().parent.parent / "noctria_gui" / "routes"
INIT_FILE = ROUTES_DIR / "__init__.py"

def find_router_modules():
    """
    🔍 routes/ 配下の router 定義モジュールを収集
    """
    modules = []
    for file in ROUTES_DIR.glob("*.py"):
        if file.name.startswith("_") or file.name == "__init__.py":
            continue
        module_name = file.stem
        modules.append(module_name)
    return sorted(modules)


def generate_init_content(modules):
    """
    🧩 __init__.py の内容を生成
    """
    lines = []
    lines.append("#!/usr/bin/env python3")
    lines.append("# coding: utf-8\n")
    lines.append('"""\n📦 noctria_gui.routes\n- 自動生成された router 一括登録ファイル\n"""\n')
    lines.append("import importlib")
    lines.append("from fastapi import APIRouter")
    lines.append("from typing import List\n")
    lines.append("routers: List[APIRouter] = []\n")
    lines.append("# 🔁 自動インポート（generated）")
    lines.append("__path__ = __path__  # required for pkgutil\n")

    for name in modules:
        lines.append(f"try:")
        lines.append(f"    mod = importlib.import_module(f\".{{name}}\", package=__name__)")
        lines.append(f"    if hasattr(mod, \"router\"):")
        lines.append(f"        routers.append(mod.router)")
        lines.append(f"        print(f\"[routes] ✅ router 読込成功: {name}\")")
        lines.append(f"    else:")
        lines.append(f"        print(f\"[routes] ⚠️ router 未定義: {name}\")")
        lines.append(f"except Exception as e:")
        lines.append(f"    print(f\"[routes] ❌ router 読込失敗: {name} - {{repr(e)}}\")\n")

    return "\n".join(lines)


def main():
    modules = find_router_modules()
    content = generate_init_content(modules)

    try:
        INIT_FILE.write_text(content, encoding="utf-8")
        print(f"✅ routes/__init__.py を再生成しました: {INIT_FILE}")
    except Exception as e:
        print(f"❌ 書き込み失敗: {e}")


if __name__ == "__main__":
    main()
