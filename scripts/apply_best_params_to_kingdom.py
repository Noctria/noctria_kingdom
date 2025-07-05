#!/usr/bin/env python3
# coding: utf-8

import shutil
from pathlib import Path
import json

from core.path_config import LOGS_DIR, MODELS_DIR, STRATEGIES_DIR
from core.logger import setup_logger  # 🏰 王国記録係の導入

# ✅ 王国記録の保存先を定義
logger = setup_logger("kingdom_logger", LOGS_DIR / "pdca" / "kingdom_apply.log")

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

    logger.info("👑 王命: 最適戦略の王国昇格処理を開始する")

    # モデル反映
    if model_src.exists():
        try:
            model_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(model_src, model_dst)
            logger.info(f"📦 モデルを正式戦略として反映: {model_dst}")
        except Exception as e:
            logger.error(f"❌ モデル反映失敗: {e}")
            raise
    else:
        logger.error(f"❌ モデルが存在しません: {model_src}")

    # パラメータ反映
    if params_src.exists():
        try:
            params_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(params_src, params_dst)
            logger.info(f"📘 パラメータを正式戦略として反映: {params_dst}")
        except Exception as e:
            logger.error(f"❌ パラメータ反映失敗: {e}")
            raise
    else:
        logger.error(f"❌ パラメータが存在しません: {params_src}")

    logger.info("🎉 王国への反映処理が完了しました")

# ✅ テスト用実行
if __name__ == "__main__":
    logger.info("⚔️ CLI起動: 王国への戦略昇格を実行中")
    apply_best_params_to_kingdom()
    logger.info("🌟 王国戦略の昇格処理が正常に終了しました")
