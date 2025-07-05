import shutil
import json
from pathlib import Path
from core.path_config import VERITAS_EVAL_LOG, STRATEGIES_DIR

# ========================================
# ⚔️ Veritas戦略昇格スクリプト（Actフェーズ）
# ========================================

EVAL_LOG_PATH = VERITAS_EVAL_LOG
SOURCE_DIR = STRATEGIES_DIR / "veritas_generated"
DEST_DIR = STRATEGIES_DIR / "official"

# ✅ Airflow対応関数（引数なし）
def promote_strategies():
    print("👑 [Veritas] 採用戦略の昇格フェーズを開始します…")

    # 📁 昇格先ディレクトリを作成（存在しない場合）
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    # 📖 評価ログの読み込み
    if not EVAL_LOG_PATH.exists():
        print("⚠️ 評価ログが存在しません:", EVAL_LOG_PATH)
        return

    with open(EVAL_LOG_PATH, "r", encoding="utf-8") as f:
        evaluation_results = json.load(f)

    # 🎯 採用戦略の昇格処理
    promoted = []
    for entry in evaluation_results:
        if entry.get("passed"):  # ← Airflow評価結果では "passed" キー
            filename = entry.get("strategy") or entry.get("filename")
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

# ✅ 手動実行用
if __name__ == "__main__":
    promote_strategies()
