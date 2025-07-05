#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Noctria Kingdom 路構図（path_config）の整合性検査スクリプト v2
- `--strict`: 存在しない項目があると終了コード 1 を返す
- `--show-paths`: 各キーのフルパスも表示
"""

import argparse
from core import path_config

def main():
    parser = argparse.ArgumentParser(
        description="🔍 Noctria Kingdom 路構図の整合性を検査します。"
    )
    parser.add_argument("--strict", action="store_true", help="❗ エラー時に終了コード 1 を返す")
    parser.add_argument("--show-paths", action="store_true", help="📂 各パスのフルパスを表示する")

    args = parser.parse_args()
    result = path_config._lint_path_config()
    passed = True

    print("🛡️ Noctria Kingdom 路構図の整合性検査を開始します...\n")

    for key, exists in result.items():
        path_obj = getattr(path_config, key, None)
        if exists:
            status = f"✅ {key}"
        else:
            status = f"❌ {key} が存在しません"
            passed = False

        if args.show_paths and isinstance(path_obj, object):
            status += f" → {path_obj}"
        print(status)

    print("\n📜 検査完了。")
    if passed:
        print("🎉 全ての構成パスが整っています。王国の秩序は保たれています。")
        exit(0)
    else:
        print("⚠️ 一部の構成に問題があります。地図（path_config.py）と実構造を確認してください。")
        if args.strict:
            exit(1)
        else:
            exit(0)

if __name__ == "__main__":
    main()
