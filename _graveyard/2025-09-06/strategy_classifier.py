#!/usr/bin/env python3
# coding: utf-8

import os
import shutil
import re
from pathlib import Path

from core.path_config import STRATEGY_OFFICIAL_DIR

# === ヘッダーコメントからメタ情報を抽出する ===
def extract_metadata_from_file(file_path):
    asset = None
    strategy_type = None
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            asset_match = re.match(r"#\s*asset\s*:\s*(\w+)", line, re.IGNORECASE)
            type_match = re.match(r"#\s*type\s*:\s*(\w+)", line, re.IGNORECASE)
            if asset_match:
                asset = asset_match.group(1).upper()
            if type_match:
                strategy_type = type_match.group(1).lower()
            if asset and strategy_type:
                break
    return asset, strategy_type

# === ファイルを分類先へ移動する ===
def classify_strategies():
    base_dir = Path(STRATEGY_OFFICIAL_DIR)
    moved_count = 0

    for file in base_dir.glob("*.py"):
        asset, strategy_type = extract_metadata_from_file(file)
        if not asset or not strategy_type:
            print(f"⚠️ メタ情報不足のため分類不可: {file.name}")
            continue

        dest_dir = base_dir / asset / strategy_type
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file.name

        shutil.move(str(file), str(dest_path))
        print(f"✅ {file.name} を {asset}/{strategy_type}/ に移動しました")
        moved_count += 1

    if moved_count == 0:
        print("🔍 分類対象ファイルはありませんでした。")

if __name__ == "__main__":
    print("👑 Noctria Kingdom: 戦略分類スクリプト 起動")
    classify_strategies()
