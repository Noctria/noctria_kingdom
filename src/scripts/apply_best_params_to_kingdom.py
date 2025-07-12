#!/usr/bin/env python3
# coding: utf-8

import shutil
import json
from pathlib import Path
from typing import Dict, Any
import sys
import os

# core パスのインポート対応
try:
    from core.path_config import *
    from core.logger import setup_logger
except ImportError:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from core.path_config import *
    from core.logger import setup_logger

# ✅ ロガー設定
logger = setup_logger("kingdom_apply_script", LOGS_DIR / "pdca" / "kingdom_apply.log")


# ================================================
# 🎯 DAG から呼び出される昇格関数
# ================================================
def apply_best_params_to_kingdom(
    new_model_info: Dict[str, Any],
    min_improvement_threshold: float = 0.01
) -> None:
    """
    ✅ 新モデルの評価スコアが現行モデルを超えた場合、王国（公式）モデルとして昇格
    """
    from datetime import datetime  # ✅ 遅延インポート（Airflow対策）

    if not new_model_info or "model_path" not in new_model_info or "evaluation_score" not in new_model_info:
        logger.error(f"❌ 無効なモデル情報が提供されました: {new_model_info}")
        raise ValueError("Invalid model_info provided.")

    new_model_path = Path(new_model_info["model_path"])
    new_model_score = new_model_info["evaluation_score"]

    logger.info("👑 王命: 最適戦略の王国昇格プロセスを開始する")
    logger.info(f"   - 新モデル候補: {new_model_path.name}")
    logger.info(f"   - 新モデルスコア: {new_model_score:.4f}")

    official_dir = MODELS_DIR / "official"
    model_registry_path = official_dir / "model_registry.json"
    current_production_score = float('-inf')

    # 🔍 現行モデルスコアの取得
    if model_registry_path.exists():
        try:
            with open(model_registry_path, "r") as f:
                registry = json.load(f)
                current_production_score = registry.get("production", {}).get("evaluation_score", float('-inf'))
            logger.info(f"   - 現行モデルスコア: {current_production_score:.4f}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"⚠️ レジストリ読み込み失敗: {e}（昇格は継続）")

    # 🚨 セーフティゲート：新モデルが基準を超えているか？
    if new_model_score < current_production_score + min_improvement_threshold:
        logger.warning(f"⚠️ 昇格見送り: 新モデルのスコア({new_model_score:.4f})が基準に達していません。")
        return

    logger.info("✅ 昇格承認: 新モデルが基準を上回りました。")

    try:
        official_dir.mkdir(parents=True, exist_ok=True)

        # 1️⃣ モデルファイルを公式ディレクトリにコピー
        promoted_model_path = official_dir / new_model_path.name
        shutil.copy2(new_model_path, promoted_model_path)
        logger.info(f"📦 モデル配置完了: {promoted_model_path}")

        # 2️⃣ レジストリ更新
        registry_data = {
            "production": {
                "model_path": str(promoted_model_path.relative_to(MODELS_DIR)),
                "evaluation_score": new_model_score,
                "promoted_at": datetime.now().isoformat()
            },
            "history": registry.get("history", []) if 'registry' in locals() else []
        }
        if 'registry' in locals() and "production" in registry:
            registry_data["history"].insert(0, registry["production"])
            registry_data["history"] = registry_data["history"][:10]

        with open(model_registry_path, "w") as f:
            json.dump(registry_data, f, indent=2)
        logger.info(f"📘 モデルレジストリを更新しました: {model_registry_path}")

    except Exception as e:
        logger.error(f"❌ 昇格処理エラー: {e}", exc_info=True)
        raise

    logger.info("🎉 王国への反映が完了しました！")


# ================================================
# 🧪 CLI テスト実行（開発・デバッグ用）
# ================================================
if __name__ == "__main__":
    from datetime import datetime
    logger.info("⚔️ CLI起動: 王国への戦略昇格テスト実行中")

    mock_model_info = {
        "model_path": str(MODELS_DIR / "metaai_model_20250712-123456.zip"),
        "evaluation_score": 250.0
    }
    if not Path(mock_model_info["model_path"]).exists():
        Path(mock_model_info["model_path"]).touch()

    apply_best_params_to_kingdom(new_model_info=mock_model_info)
    logger.info("🌟 テスト完了: 王国戦略の昇格処理が終了しました")
