from __future__ import annotations

import json
import logging
import math
import os
import shutil
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ------------------------------------------------------------
# ロガー（プロジェクト共通ロガーがあれば利用、無ければ標準logging）
# ------------------------------------------------------------
def _setup_logger() -> logging.Logger:
    logger_name = "ApplyBestParamsToKingdom"
    try:
        from src.core.path_config import LOGS_DIR  # type: ignore
        from src.core.logger import setup_logger  # type: ignore

        log_path = Path(LOGS_DIR) / "scripts" / "apply_best_params_to_kingdom.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return setup_logger(logger_name, log_path)
    except Exception:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s - %(message)s",
        )
        return logging.getLogger(logger_name)


logger = _setup_logger()

# ------------------------------------------------------------
# パス設定（環境変数で上書き可）
#   - NOCTRIA_MODELS_DIR : /opt/airflow/data/models を想定
#   - NOCTRIA_PRODUCTION_DIR : 省略時は {MODELS_DIR}/production
#   - NOCTRIA_PRODUCTION_LATEST_NAME : 省略時 "metaai_production_latest.zip"
#   - NOCTRIA_PRODUCTION_META_NAME   : 省略時 "metaai_production_metadata.json"
# ------------------------------------------------------------
MODELS_DIR = Path(os.environ.get("NOCTRIA_MODELS_DIR", "/opt/airflow/data/models"))
PRODUCTION_DIR = Path(
    os.environ.get("NOCTRIA_PRODUCTION_DIR", str(MODELS_DIR / "production"))
)
LATEST_NAME = os.environ.get("NOCTRIA_PRODUCTION_LATEST_NAME", "metaai_production_latest.zip")
META_NAME = os.environ.get("NOCTRIA_PRODUCTION_META_NAME", "metaai_production_metadata.json")

PRODUCTION_DIR.mkdir(parents=True, exist_ok=True)
(MODELS_DIR).mkdir(parents=True, exist_ok=True)

LATEST_PATH = PRODUCTION_DIR / LATEST_NAME
META_PATH = PRODUCTION_DIR / META_NAME


# ------------------------------------------------------------
# ユーティリティ：安全コピー（copy2→フォールバック）
# ------------------------------------------------------------
def _atomic_copy(src: str | Path, dst: str | Path) -> None:
    """メタデータ無視の生コピーを一時ファイル経由で atomic に入れ替える。"""
    src = str(src)
    dst = str(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    tmp = None
    try:
        dstdir = os.path.dirname(dst)
        with tempfile.NamedTemporaryFile(dir=dstdir, delete=False) as tf:
            tmp = tf.name
        shutil.copyfile(src, tmp)
        try:
            os.replace(tmp, dst)  # atomic swap
            tmp = None
        except PermissionError:
            # 一部FSで os.replace も拒否される場合の最終手段
            shutil.copyfile(tmp, dst)
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except Exception:
                pass


def _safe_copy(src: str | Path, dst: str | Path) -> None:
    """まず copy2 を試し、EPERM などで失敗したら raw copy + atomic replace。"""
    src = str(src)
    dst = str(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        shutil.copy2(src, dst)  # メタデータも含めてコピー（同一FSなら速い）
    except PermissionError:
        _atomic_copy(src, dst)


def _safe_point_latest(latest_path: str | Path, target_path: str | Path) -> None:
    """
    latest シンボリックリンクを張る。不可なら実体コピーにフォールバック。
    """
    latest_path = str(latest_path)
    target_path = str(target_path)
    try:
        if os.path.islink(latest_path) or os.path.exists(latest_path):
            try:
                os.remove(latest_path)
            except PermissionError:
                # 削除不可なら上書きで逃げる
                pass
        os.symlink(os.path.basename(target_path), latest_path)
    except OSError:
        # シンボリックリンクが許可されないFSの場合
        _atomic_copy(target_path, latest_path)


# ------------------------------------------------------------
# メタデータのロード/セーブ
# ------------------------------------------------------------
def _load_meta(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"メタデータ読み込み失敗: {path} ({e})")
        return {}


def _save_meta(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ------------------------------------------------------------
# メイン関数：昇格ロジック
#   引数 model_info 例:
#   {
#     "model_path": "/opt/airflow/data/models/metaai_model_20250810-175800.zip",
#     "evaluation_score": 0.0,
#     "params": {...},
#     "version": "20250810-175800",
#     ...
#   }
# 戻り値:
#   {
#     "status": "OK" | "SKIP" | "ERROR",
#     "detail": "...",
#     "production_model_path": "/opt/airflow/data/models/production/metaai_model_20250810-175800.zip",
#     "new_score": 0.0,
#     "old_score": -inf
#   }
# ------------------------------------------------------------
def apply_best_params_to_kingdom(model_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not model_info:
        detail = "model_info が空です"
        logger.warning(detail)
        return {
            "status": "ERROR",
            "detail": detail,
            "production_model_path": None,
            "new_score": float("nan"),
            "old_score": float("nan"),
        }

    try:
        new_model_path = Path(str(model_info.get("model_path", "")))
        new_score = float(model_info.get("evaluation_score", 0.0))
        version = str(model_info.get("version", datetime.utcnow().strftime("%Y%m%d-%H%M%S")))

        if not new_model_path.exists():
            detail = f"候補モデルが存在しません: {new_model_path}"
            logger.error(detail)
            return {
                "status": "ERROR",
                "detail": detail,
                "production_model_path": None,
                "new_score": new_score,
                "old_score": float("nan"),
            }

        logger.info(f"👑 昇格判定開始 | 候補: {new_model_path.name} | score={new_score:.4f}")

        # 旧メタデータ読込
        meta = _load_meta(META_PATH)
        old_score = float(meta.get("score", float("-inf")))
        old_model = meta.get("model_path")

        # 比較（良ければ昇格）
        if new_score <= old_score:
            reason = f"新スコア {new_score:.4f} <= 旧スコア {old_score:.4f} のため昇格スキップ"
            logger.info(f"⏭ {reason}")
            return {
                "status": "SKIP",
                "detail": reason,
                "production_model_path": str(old_model) if old_model else None,
                "new_score": new_score,
                "old_score": old_score,
            }

        # 昇格先パス（ファイル名はそのまま採用）
        promoted_model_path = PRODUCTION_DIR / new_model_path.name
        _safe_copy(new_model_path, promoted_model_path)

        # latest を指す（リンク不可なら実体コピー）
        _safe_point_latest(LATEST_PATH, promoted_model_path)

        # メタデータ更新
        new_meta = {
            "model_path": str(promoted_model_path),
            "score": new_score,
            "version": version,
            "promoted_at_utc": datetime.utcnow().isoformat(),
            "source_model": str(new_model_path),
            "latest_alias": str(LATEST_PATH),
        }
        _save_meta(META_PATH, new_meta)

        logger.info(f"✅ 昇格完了: {promoted_model_path}（score {new_score:.4f} > {old_score:.4f}）")
        return {
            "status": "OK",
            "detail": "promoted",
            "production_model_path": str(promoted_model_path),
            "new_score": new_score,
            "old_score": old_score,
        }

    except Exception as e:
        detail = f"モデルコピー失敗: {e}"
        logger.error(detail)
        logger.debug(traceback.format_exc())
        return {
            "status": "ERROR",
            "detail": detail,
            "error": traceback.format_exc(),
            "production_model_path": None,
            "new_score": float(model_info.get("evaluation_score", 0.0)) if model_info else float("nan"),
            "old_score": float("-inf"),
        }


# ------------------------------------------------------------
# 単体テスト用（任意実行）
# ------------------------------------------------------------
if __name__ == "__main__":
    # ダミーで呼び出せるように
    dummy = {
        "model_path": str(MODELS_DIR / "metaai_model_dummy.zip"),
        "evaluation_score": 0.0,
        "version": "localtest",
    }
    print(apply_best_params_to_kingdom(dummy))
