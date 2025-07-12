#!/usr/bin/env python3
# coding: utf-8

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import sys
import os

# coreパスの解決（Airflow & CLI 両対応）
try:
    from core.path_config import *
    from core.logger import setup_logger
    from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
except ImportError:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from core.path_config import *
    from core.logger import setup_logger
    from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals

# ロガー設定
logger = setup_logger("metaai_apply_script", LOGS_DIR / "pdca" / "metaai_apply.log")

# ================================================
# 🚀 MetaAI再学習＆保存関数（Airflow DAGから呼ばれる）
# ================================================
def apply_best_params_to_metaai(
    best_params: Dict[str, Any],
    total_timesteps: int = 50000,
    n_eval_episodes: int = 20,
    model_version: str = None
) -> Dict[str, Any]:
    """
    ✅ MetaAIに最適パラメータを適用し再学習・評価・保存を行い、結果を返す
    """
    if not best_params:
        logger.error("❌ 最適化パラメータが提供されませんでした。")
        raise ValueError("best_params cannot be None or empty.")

    logger.info(f"📦 受け取った最適パラメータ: {best_params}")

    # ===============================
    # ⏬ 遅延インポート（Airflow DAG対策）
    # ===============================
    from stable_baselines3 import PPO
    from stable_baselines3.common.evaluation import evaluate_policy

    # ===============================
    # 📁 モデル保存パスの構築
    # ===============================
    data_path = MARKET_DATA_CSV
    tensorboard_log_dir = LOGS_DIR / "ppo_tensorboard_logs"
    version = model_version if model_version else datetime.now().strftime("%Y%m%d-%H%M%S")
    model_save_path = MODELS_DIR / f"metaai_model_{version}.zip"
    latest_model_symlink = MODELS_DIR / "metaai_model_latest.zip"

    # ===============================
    # 🌱 環境初期化
    # ===============================
    try:
        env = TradingEnvWithFundamentals(str(data_path))
        eval_env = TradingEnvWithFundamentals(str(data_path))
        logger.info("🌱 環境の初期化成功")
    except Exception as e:
        logger.error(f"❌ 環境初期化失敗: {e}", exc_info=True)
        raise

    # ===============================
    # 🛠 モデル構築
    # ===============================
    try:
        model = PPO(
            "MlpPolicy",
            env,
            verbose=0,
            tensorboard_log=str(tensorboard_log_dir),
            **best_params
        )
        logger.info("🛠 PPOモデル構築成功")
    except Exception as e:
        logger.error(f"❌ モデル構築失敗: {e}", exc_info=True)
        raise

    # ===============================
    # 🎓 再学習
    # ===============================
    try:
        logger.info(f"⚙️ MetaAI: 再学習を開始 (Timesteps: {total_timesteps})")
        model.learn(total_timesteps=total_timesteps)
        logger.info("✅ 再学習完了")
    except Exception as e:
        logger.error(f"❌ モデル学習中のエラー: {e}", exc_info=True)
        raise

    # ===============================
    # 🧪 最終評価
    # ===============================
    try:
        final_mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=n_eval_episodes)
        logger.info(f"🏆 最終評価スコア: {final_mean_reward:.4f}")
    except Exception as e:
        logger.error(f"❌ 評価失敗（スコア=-9999で続行）: {e}", exc_info=True)
        final_mean_reward = -9999.0

    # ===============================
    # 💾 モデル保存 + 最新リンク更新
    # ===============================
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model.save(model_save_path)
        logger.info(f"📁 モデル保存完了: {model_save_path}")

        if latest_model_symlink.is_symlink() or latest_model_symlink.exists():
            latest_model_symlink.unlink()
        latest_model_symlink.symlink_to(model_save_path)
        logger.info(f"🔗 シンボリックリンク更新: {latest_model_symlink.name} -> {model_save_path.name}")
    except Exception as e:
        logger.error(f"❌ モデル保存中のエラー: {e}", exc_info=True)
        raise

    return {
        "model_path": str(model_save_path),
        "evaluation_score": final_mean_reward
    }

# ================================================
# 🧪 CLIテスト実行用
# ================================================
if __name__ == "__main__":
    logger.info("🧪 CLIテスト実行開始")

    mock_best_params = {
        'learning_rate': 0.0001,
        'n_steps': 1024,
        'gamma': 0.99,
        'ent_coef': 0.01,
        'clip_range': 0.2
    }

    result = apply_best_params_to_metaai(
        best_params=mock_best_params,
        total_timesteps=1000,
        n_eval_episodes=2
    )

    logger.info(f"✅ テスト完了: {result}")
