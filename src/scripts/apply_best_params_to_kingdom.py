#!/usr/bin/env python3
# coding: utf-8

import shutil
import json
from pathlib import Path
from typing import Dict, Any

# Airflowのコンテキストから呼び出された場合、coreパッケージをインポート可能にする
import sys
import os
try:
    from core.path_config import *
    from core.logger import setup_logger
except ImportError:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from core.path_config import *
    from core.logger import setup_logger

# ✅ 王国記録係の導入
logger = setup_logger("kingdom_apply_script", LOGS_DIR / "pdca" / "kingdom_apply.log")

# ================================================
# ★改善点: DAGから直接呼び出されるメイン関数
# ================================================
def apply_best_params_to_kingdom(
    new_model_info: Dict[str, Any],
    min_improvement_threshold: float = 0.01
) -> None:
    """
    ✅ 新しいモデルを評価し、性能が向上していればNoctria Kingdomに正式反映（昇格）させる
    
    引数:
        new_model_info (dict): 前のタスクから渡された新しいモデルの情報
                               (例: {'model_path': 'path/to/model.zip', 'evaluation_score': 150.0})
        min_improvement_threshold (float): 昇格に必要となる、現行モデルに対する最低改善スコア
    """
    if not new_model_info or "model_path" not in new_model_info or "evaluation_score" not in new_model_info:
        logger.error(f"❌ 無効なモデル情報が提供されました: {new_model_info}")
        raise ValueError("Invalid model_info provided.")

    new_model_path = Path(new_model_info["model_path"])
    new_model_score = new_model_info["evaluation_score"]
    
    logger.info("👑 王命: 最適戦略の王国昇格プロセスを開始する")
    logger.info(f"   - 新モデル候補: {new_model_path.name}")
    logger.info(f"   - 新モデルスコア: {new_model_score:.4f}")

    # --- ★追加: モデルレジストリとセーフティゲート ---
    official_dir = MODELS_DIR / "official"
    model_registry_path = official_dir / "model_registry.json"
    
    current_production_score = float('-inf')

    # 現在の公式モデルのスコアを取得
    if model_registry_path.exists():
        try:
            with open(model_registry_path, "r") as f:
                registry = json.load(f)
                current_production_score = registry.get("production", {}).get("evaluation_score", float('-inf'))
            logger.info(f"   - 現行モデルスコア: {current_production_score:.4f}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"⚠️ レジストリファイルの読み込みに失敗しました: {e}。昇格を続行します。")

    # セーフティゲート: 新モデルのスコアが、現行モデルのスコアを閾値以上に上回っているか？
    if new_model_score < current_production_score + min_improvement_threshold:
        logger.warning(f"⚠️ 昇格見送り: 新モデルのスコア({new_model_score:.4f})が、現行モデルのスコア({current_production_score:.4f})と閾値({min_improvement_threshold})を上回りませんでした。")
        return # 処理を終了

    logger.info(f"✅ 昇格承認: 新モデルのスコアが基準をクリアしました。")

    # --- 昇格処理 ---
    try:
        official_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 新しいモデルファイルを公式ディレクトリにコピー
        promoted_model_path = official_dir / new_model_path.name
        shutil.copy2(new_model_path, promoted_model_path)
        logger.info(f"📦 モデルを正式戦略として配置: {promoted_model_path}")

        # 2. 新しいモデルの情報をレジストリに記録
        registry_data = {
            "production": {
                "model_path": str(promoted_model_path.relative_to(MODELS_DIR)),
                "evaluation_score": new_model_score,
                "promoted_at": datetime.now().isoformat()
            },
            "history": registry.get("history", []) if 'registry' in locals() else []
        }
        # 古いproductionをhistoryに追加
        if 'registry' in locals() and "production" in registry:
            registry_data["history"].insert(0, registry["production"])
            registry_data["history"] = registry_data["history"][:10] # 最新10件を保持
        
        with open(model_registry_path, "w") as f:
            json.dump(registry_data, f, indent=2)
        logger.info(f"📘 モデルレジストリを更新しました: {model_registry_path}")

    except Exception as e:
        logger.error(f"❌ 昇格処理中にエラーが発生しました: {e}", exc_info=True)
        raise

    logger.info("🎉 王国への反映処理が完了しました！")

# ================================================
# CLI実行時（ローカルでのデバッグ用）
# ================================================
if __name__ == "__main__":
    logger.info("⚔️ CLI起動: 王国への戦略昇格をテスト実行中")

    # --- デバッグ用のダミーモデル情報 ---
    mock_model_info = {
        "model_path": str(MODELS_DIR / "metaai_model_20250712-123456.zip"),
        "evaluation_score": 250.0
    }
    # ダミーファイルを作成
    if not Path(mock_model_info["model_path"]).exists():
        Path(mock_model_info["model_path"]).touch()

    apply_best_params_to_kingdom(model_info=mock_model_info)
    logger.info("🌟 王国戦略の昇格処理が正常に終了しました")
