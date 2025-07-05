import os
import shutil
import json
from pathlib import Path

# ========================================
# ⚔️ Veritas戦略昇格スクリプト（Actフェーズ）
# ========================================

# 📌 ディレクトリ設定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_LOG_PATH = PROJECT_ROOT / "veritas" / "evaluation_results.json"
SOURCE_DIR = PROJECT_ROOT / "strategies" / "veritas_generated"
DEST_DIR = PROJECT_ROOT / "strategies" / "official"

# 📁 昇格先ディレクトリを作成（存在しない場合）
DEST_DIR.mkdir(parents=True, exist_ok=True)

# 📖 評価結果の読み込み
if not EVAL_LOG_PATH.exists():
    print("⚠️ 評価ログが存在しません:", EVAL_LOG_PATH)
    exit(1)

with open(EVAL_LOG_PATH, "r") as f:
    evaluation_results = json.load(f)

# 🎯 採用戦略の抽出と昇格処理
promoted = []
for entry in evaluation_results:
    if entry.get("accepted"):
        filename = entry.get("filename")
        src_path = SOURCE_DIR / filename
        dst_path = DEST_DIR / filename

        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            promoted.append(filename)
            print(f"🛡️ 昇格完了: {filename}")
        else:
            print(f"⚠️ 戦略ファイルが見つかりません: {filename}")

# 📜 結果ログ
if promoted:
    print("\n🏰 王国訓示：")
    print("「選ばれし知性よ、いまこそ王国の剣として輝け。」\n")
    print("✅ 昇格された戦略一覧:")
    for f in promoted:
        print(" -", f)
else:
    print("🚫 昇格対象の戦略はありません。")

