#!/usr/bin/env python3
# coding: utf-8
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# ===== Airflow/CLI 両対応の安定 import（src. へ統一） =====
try:
    # 通常ルート（Airflowコンテナ内想定）
    from src.core.path_config import DATA_DIR, LOGS_DIR, MARKET_DATA_CSV
    from src.core.logger import setup_logger
    from src.core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
except Exception:
    # 直接実行やカレントズレ時のフォールバック:
    # <repo>/src/scripts/apply_best_params_to_metaai.py から見て repo ルートを sys.path に追加
    this_file = Path(__file__).resolve()
    project_root = this_file.parents[2]  # .../src/scripts/ -> .../src -> .../<repo>
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    from src.core.path_config import DATA_DIR, LOGS_DIR, MARKET_DATA_CSV
    from src.core.logger import setup_logger
    from src.core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals

# ログ出力（pdcaサブディレクトリを確実に用意）
(LOGS_DIR / "pdca").mkdir(parents=True, exist_ok=True)
logger = setup_logger("metaai_apply_script", LOGS_DIR / "pdca" / "metaai_apply.log")


def _safe_symlink(src: Path, dst: Path) -> None:
    """Windows/WSL でも落ちにくいシンボリックリンク更新（失敗時はコピー退避）。"""
    try:
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        dst.symlink_to(src, target_is_directory=False)
    except Exception:
        # 権限などで失敗したらコピーで代替
        import shutil
        shutil.copy2(src, dst)


def apply_best_params_to_metaai(
    best_params: Dict[str, Any],
    total_timesteps: int = 50_000,
    n_eval_episodes: int = 20,
    model_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ✅ MetaAIに最適パラメータを適用して再学習→評価→保存。
    戻り値は下流（PDCA監査/GUI）で使いやすいメタ情報を含む。
    """
    if not best_params:
        raise ValueError("best_params cannot be empty.")

    logger.info("📦 受領パラメータ: %s", json.dumps(best_params, ensure_ascii=False))

    # 遅延import（Airflowワーカーでの起動安定化）
    from stable_baselines3 import PPO
    from stable_baselines3.common.evaluation import evaluate_policy

    # パス構築（path_config に MODELS_DIR は無い前提 → data/models/ に保存）
    MODELS_DIR = DATA_DIR / "models"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    version = model_version or datetime.now().strftime("%Y%m%d-%H%M%S")
    model_save_path = MODELS_DIR / f"metaai_model_{version}.zip"
    latest_model_alias = MODELS_DIR / "metaai_model_latest.zip"
    tensorboard_log_dir = LOGS_DIR / "ppo_tensorboard_logs"

    # 環境準備
    env = TradingEnvWithFundamentals(str(MARKET_DATA_CSV))
    eval_env = TradingEnvWithFundamentals(str(MARKET_DATA_CSV))

    try:
        model = PPO(
            "MlpPolicy",
            env,
            verbose=0,
            tensorboard_log=str(tensorboard_log_dir),
            **best_params,
        )
        logger.info("🛠 PPOモデル構築OK")
        logger.info("⚙️ 再学習開始: timesteps=%d", total_timesteps)
        model.learn(total_timesteps=total_timesteps)
        logger.info("✅ 学習完了")

        # 評価（例外時は -9999 継続）
        try:
            final_mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=n_eval_episodes)
        except Exception as e:
            logger.exception("評価失敗（-9999継続）: %s", e)
            final_mean_reward = -9999.0

        # 保存＆エイリアス更新
        model.save(model_save_path)
        _safe_symlink(model_save_path, latest_model_alias)
        logger.info("📁 保存: %s / 最新リンク: %s", model_save_path, latest_model_alias)

        # 戻り値（DAG下流や監査で活用）
        result = {
            "model_path": str(model_save_path),
            "evaluation_score": float(final_mean_reward),
            "params": best_params,
            "version": version,
            "data_source": str(MARKET_DATA_CSV),
            "tensorboard_log_dir": str(tensorboard_log_dir),
        }
        return result

    finally:
        # 後処理は必ず実行
        try:
            env.close()
            eval_env.close()
        except Exception:
            pass
        logger.info("🧹 環境クローズ")


if __name__ == "__main__":
    mock_best_params = dict(learning_rate=1e-4, n_steps=1024, gamma=0.99, ent_coef=0.01, clip_range=0.2)
    r = apply_best_params_to_metaai(best_params=mock_best_params, total_timesteps=1_000, n_eval_episodes=2)
    print(json.dumps(r, indent=2, ensure_ascii=False))
