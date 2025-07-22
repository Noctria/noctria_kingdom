#!/usr/bin/env python3
# coding: utf-8

"""
⚔️ Veritas Machina - 戦略昇格スクリプト（ML/Act専用）
- ML戦略評価ログ（JSON）から合格戦略ファイルのみ“公式ディレクトリ”へ昇格
- Airflowワークフローにも対応
"""

import shutil
import json
from pathlib import Path
from src.core.path_config import VERITAS_EVAL_LOG, STRATEGIES_DIR

# ========================================
# 🏅 Veritas ML戦略昇格パス
# ========================================
EVAL_LOG_PATH = VERITAS_EVAL_LOG
SOURCE_DIR = STRATEGIES_DIR / "veritas_generated"
DEST_DIR = STRATEGIES_DIR / "official"

def promote_accepted_strategies():
    print("👑 [Veritas Machina] 合格戦略の公式昇格処理を開始…")
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    if not EVAL_LOG_PATH.exists():
        print("⚠️ 評価ログが存在しません:", EVAL_LOG_PATH)
        return

    with open(EVAL_LOG_PATH, "r", encoding="utf-8") as f:
        evaluation_results = json.load(f)

    promoted = []
    for entry in evaluation_results:
        if entry.get("passed"):  # ML評価フェーズで "passed" キー
            filename = entry.get("strategy") or entry.get("filename")
            src_path = SOURCE_DIR / filename
            dst_path = DEST_DIR / filename

            if src_path.exists():
                shutil.copy2(src_path, dst_path)
                promoted.append(filename)
                print(f"🛡️ 昇格完了: {filename}")
            else:
                print(f"⚠️ 戦略ファイルが見つかりません: {filename}")

    if promoted:
        print("\n🏰 王国訓示：")
        print("「選ばれし知性よ、いまこそ王国の剣として輝け。」\n")
        print("✅ 昇格されたML戦略一覧:")
        for f in promoted:
            print(" -", f)
    else:
        print("🚫 昇格対象の戦略はありません。")

if __name__ == "__main__":
    promote_accepted_strategies()
