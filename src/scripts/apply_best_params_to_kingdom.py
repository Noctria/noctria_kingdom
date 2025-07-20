#!/usr/bin/env python3
# coding: utf-8

import shutil
import json
from pathlib import Path
from typing import Dict, Any
import sys
import os
import traceback

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

logger = setup_logger("kingdom_apply_script", LOGS_DIR / "pdca" / "kingdom_apply.log")

# ================================================
# 🎯 DAG から呼び出される昇格関数（raise撤廃ver）
# ================================================
def apply_best_params_to_kingdom(
    model_info: Dict[str, Any],
    min_improvement_threshold: float = 0.01
) -> Dict[str, Any]:
    """
    ✅ 新モデルの評価スコアが現行モデルを超えた場合、王国（公式）モデルとして昇格
    戻り値: dict（status, detail, error 等）
    """
    from datetime import datetime  # ✅ 遅延インポート（Airflow対策）
    result = {"status": "ERROR", "detail": "", "error": ""}

    try:
        # 必須項目チェック
        if not model_info or "model_path" not in model_info or "evaluation_score" not in model_info:
            msg = f"❌ 無効なモデル情報が提供されました: {model_info}"
            logger.error(msg)
            result["detail"] = msg
            return result

        new_model_path = Path(model_info["model_path"])
        new_model_score = model_info["evaluation_score"]

        logger.info("👑 王命: 最適戦略の王国昇格プロセスを開始する")
        logger.info(f"   - 新モデル候補: {new_model_path.name}")
        logger.info(f"   - 新モデルスコア: {new_model_score:.4f}")

        official_dir = MODELS_DIR / "official"
        model_registry_path = official_dir / "model_registry.json"
        current_production_score = float('-inf')

        # 現行モデルスコアの取得
        registry = {}
        if model_registry_path.exists():
            try:
                with open(model_registry_path, "r") as f:
                    registry = json.load(f)
                    current_production_score = registry.get("production", {}).get("evaluation_score", float('-inf'))
                logger.info(f"   - 現行モデルスコア: {current_production_score:.4f}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"⚠️ レジストリ読み込み失敗: {e}（昇格は継続）")
            except Exception as e:
                err = traceback.format_exc()
                logger.error(f"モデルレジストリ読込で致命的例外: {e}\n{err}")
                result["detail"] = f"モデルレジストリ読込で致命的例外: {e}"
                result["error"] = err
                result["status"] = "ERROR"
                return result

        # セーフティゲート：新モデルが基準を超えているか？
        if new_model_score < current_production_score + min_improvement_threshold:
            msg = f"⚠️ 昇格見送り: 新モデルのスコア({new_model_score:.4f})が基準({current_production_score:.4f}+{min_improvement_threshold:.4f})に達していません。"
            logger.warning(msg)
            result["status"] = "SKIPPED"
            result["detail"] = msg
            return result

        logger.info("✅ 昇格承認: 新モデルが基準を上回りました。")

        try:
            official_dir.mkdir(parents=True, exist_ok=True)

            # モデルファイル存在チェック
            if not new_model_path.exists():
                msg = f"❌ 新モデルファイルが見つかりません: {new_model_path}"
                logger.error(msg)
                result["status"] = "ERROR"
                result["detail"] = msg
                return result

            # モデルファイルを公式ディレクトリにコピー
            promoted_model_path = official_dir / new_model_path.name
            try:
                shutil.copy2(new_model_path, promoted_model_path)
            except Exception as e:
                err = traceback.format_exc()
                logger.error(f"モデルファイルコピー失敗: {e}\n{err}")
                result["status"] = "ERROR"
                result["detail"] = f"モデルファイルコピー失敗: {e}"
                result["error"] = err
                return result
            logger.info(f"📦 モデル配置完了: {promoted_model_path}")

            # レジストリ更新
            try:
                registry_data = {
                    "production": {
                        "model_path": str(promoted_model_path.relative_to(MODELS_DIR)),
                        "evaluation_score": new_model_score,
                        "promoted_at": datetime.now().isoformat()
                    },
                    "history": registry.get("history", []) if registry else []
                }
                if registry and "production" in registry:
                    registry_data["history"].insert(0, registry["production"])
                    registry_data["history"] = registry_data["history"][:10]

                with open(model_registry_path, "w") as f:
                    json.dump(registry_data, f, indent=2)
                logger.info(f"📘 モデルレジストリを更新しました: {model_registry_path}")
            except Exception as e:
                err = traceback.format_exc()
                logger.error(f"モデルレジストリ更新失敗: {e}\n{err}")
                result["status"] = "ERROR"
                result["detail"] = f"モデルレジストリ更新失敗: {e}"
                result["error"] = err
                return result

            logger.info("🎉 王国への反映が完了しました！")
            result["status"] = "SUCCESS"
            result["detail"] = f"昇格完了: {promoted_model_path}"
            return result

        except Exception as e:
            err = traceback.format_exc()
            logger.error(f"❌ 昇格処理エラー: {e}\n{err}")
            result["status"] = "ERROR"
            result["detail"] = f"昇格処理エラー: {e}"
            result["error"] = err
            return result

    except Exception as e:
        err = traceback.format_exc()
        logger.error(f"❌ apply_best_params_to_kingdom全体で致命的エラー: {e}\n{err}")
        result["status"] = "ERROR"
        result["detail"] = f"apply_best_params_to_kingdom全体で致命的エラー: {e}"
        result["error"] = err
        return result

    return result

# ================================================
# 🧪 CLI テスト実行（開発・デバッグ用）
# ================================================
if __name__ == "__main__":
    from datetime import datetime
    try:
        logger.info("⚔️ CLI起動: 王国への戦略昇格テスト実行中")

        mock_model_info = {
            "model_path": str(MODELS_DIR / "metaai_model_20250712-123456.zip"),
            "evaluation_score": 250.0
        }
        # テスト用: モデルファイルなければ空で作成
        if not Path(mock_model_info["model_path"]).exists():
            Path(mock_model_info["model_path"]).touch()

        result = apply_best_params_to_kingdom(model_info=mock_model_info)
        logger.info(f"🌟 テスト完了: 王国戦略の昇格処理: {result['status']} / {result.get('detail','')}")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        err = traceback.format_exc()
        logger.error(f"❌ CLIメインブロックで致命的エラー: {e}\n{err}")
        print(json.dumps({"status": "ERROR", "detail": str(e), "error": err}, ensure_ascii=False, indent=2))
