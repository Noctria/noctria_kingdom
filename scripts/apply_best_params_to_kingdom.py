# scripts/apply_best_params_to_kingdom.py

import shutil
from pathlib import Path
import json
from core.path_config import LOGS_DIR, MODELS_DIR, STRATEGIES_DIR

def apply_best_params_to_kingdom():
    """
    ✅ 最適化された戦略・モデルを Noctria Kingdom に正式反映する
    - 対象ファイル:
        - logs/metaai_model_latest.zip
        - logs/best_params.json
    - 反映先:
        - models/official/metaai_model.zip
        - strategies/official/best_params.json
    """

    model_src = LOGS_DIR / "metaai_model_latest.zip"
    model_dst = MODELS_DIR / "official" / "metaai_model.zip"

    params_src = LOGS_DIR / "best_params.json"
    params_dst = STRATEGIES_DIR / "official" / "best_params.json"

    # モデル反映
    if model_src.exists():
        model_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(model_src, model_dst)
        print(f"📦 モデルを {model_dst} に反映しました。")
    else:
        print(f"❌ モデルが存在しません: {model_src}")

    # パラメータ反映
    if params_src.exists():
        params_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(params_src, params_dst)
        print(f"📘 パラメータを {params_dst} に反映しました。")
    else:
        print(f"❌ パラメータが存在しません: {params_src}")

    print("🏁 王国への反映処理が完了しました。")

# ✅ テスト用実行
if __name__ == "__main__":
    apply_best_params_to_kingdom()
