#!/usr/bin/env python3
# coding: utf-8
from __future__ import annotations

import json
import os
import sys
import shutil
import traceback
from pathlib import Path
from typing import Dict, Any

# 安定 import（Airflow/CLI 両対応、src. へ統一）
try:
    from src.core.path_config import DATA_DIR, LOGS_DIR
    from src.core.logger import setup_logger
except Exception:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(project_root))
    from src.core.path_config import DATA_DIR, LOGS_DIR
    from src.core.logger import setup_logger

logger = setup_logger("kingdom_apply_script", LOGS_DIR / "pdca" / "kingdom_apply.log")

def apply_best_params_to_kingdom(
    model_info: Dict[str, Any],
    min_improvement_threshold: float = 0.01,
) -> Dict[str, Any]:
    """
    ✅ 新モデルの評価スコアが現行モデルより良ければ「王国（公式）」へ昇格。
    Returns: {"status","detail","error","production_model_path","new_score","old_score"}
    """
    from datetime import datetime

    result: Dict[str, Any] = {
        "status": "ERROR",
        "detail": "",
        "error": "",
        "production_model_path": None,
        "new_score": None,
        "old_score": None,
    }
    try:
        # --- 入力チェック
        if not model_info or "model_path" not in model_info or "evaluation_score" not in model_info:
            msg = f"無効なモデル情報: {model_info}"
            logger.error("❌ %s", msg)
            result["detail"] = msg
            return result

        MODELS_DIR = DATA_DIR / "models"                 # path_config v4.6 に追随
        official_dir = MODELS_DIR / "official"
        model_registry_path = official_dir / "model_registry.json"

        new_model_path = Path(model_info["model_path"])
        new_model_score = float(model_info["evaluation_score"])
        result["new_score"] = new_model_score

        logger.info("👑 昇格判定開始 | 候補: %s | score=%.4f", new_model_path.name, new_model_score)

        # --- 現行スコア取得
        current_score = float("-inf")
        registry = {}
        if model_registry_path.exists():
            try:
                registry = json.loads(model_registry_path.read_text(encoding="utf-8"))
                current_score = float(registry.get("production", {}).get("evaluation_score", float("-inf")))
                logger.info("現行スコア: %.4f", current_score)
            except Exception as e:
                logger.warning("⚠️ レジストリ読み込み失敗（継続）: %s", e)
        result["old_score"] = current_score

        # --- セーフティゲート
        threshold = current_score + float(min_improvement_threshold)
        if new_model_score < threshold:
            msg = f"昇格見送り: new={new_model_score:.4f} < threshold={threshold:.4f}"
            logger.warning("⚠️ %s", msg)
            result["status"] = "SKIPPED"
            result["detail"] = msg
            return result

        # --- ファイル検証 & 配置
        if not new_model_path.exists():
            msg = f"新モデルが見つかりません: {new_model_path}"
            logger.error("❌ %s", msg)
            result["detail"] = msg
            return result

        official_dir.mkdir(parents=True, exist_ok=True)
        promoted_model_path = official_dir / new_model_path.name
        try:
            shutil.copy2(new_model_path, promoted_model_path)
        except Exception as e:
            err = traceback.format_exc()
            logger.error("モデルコピー失敗: %s\n%s", e, err)
            result.update(status="ERROR", detail=f"モデルコピー失敗: {e}", error=err)
            return result

        # --- レジストリ更新
        try:
            history = registry.get("history", []) if registry else []
            if "production" in registry:
                history.insert(0, registry["production"])
                history = history[:10]

            registry_data = {
                "production": {
                    "model_path": str(promoted_model_path.relative_to(MODELS_DIR)),
                    "evaluation_score": new_model_score,
                    "promoted_at": datetime.now().isoformat(),
                },
                "history": history,
            }
            model_registry_path.write_text(json.dumps(registry_data, indent=2), encoding="utf-8")
            logger.info("📘 レジストリ更新: %s", model_registry_path)
        except Exception as e:
            err = traceback.format_exc()
            logger.error("レジストリ更新失敗: %s\n%s", e, err)
            result.update(status="ERROR", detail=f"レジストリ更新失敗: {e}", error=err)
            return result

        logger.info("🎉 昇格完了: %s", promoted_model_path)
        result.update(
            status="SUCCESS",
            detail=f"昇格完了: {promoted_model_path}",
            production_model_path=str(promoted_model_path),
        )
        return result

    except Exception as e:
        err = traceback.format_exc()
        logger.error("apply_best_params_to_kingdom 致命的: %s\n%s", e, err)
        result.update(detail=str(e), error=err)
        return result

if __name__ == "__main__":
    # 簡易テスト
    dummy_dir = DATA_DIR / "models"
    dummy_dir.mkdir(parents=True, exist_ok=True)
    dummy_model = dummy_dir / "metaai_model_dummy.zip"
    dummy_model.touch(exist_ok=True)
    print(json.dumps(apply_best_params_to_kingdom({"model_path": str(dummy_model), "evaluation_score": 1.23}), ensure_ascii=False, indent=2))
