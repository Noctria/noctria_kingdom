#!/usr/bin/env python3
# coding: utf-8

import json
from pathlib import Path

from stable_baselines3 import PPO

from core.meta_ai import MetaAI
from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
from core.path_config import LOGS_DIR, DATA_DIR
from core.logger import setup_logger  # ✅ 王国記録係を導入

# 🏰 王国の叡智を記録する記録係
logger = setup_logger("metaai_logger", LOGS_DIR / "pdca" / "metaai_apply.log")

def apply_best_params_to_metaai():
    """
    ✅ MetaAIに最適パラメータを適用し再学習を行うスクリプト
    - 使用ファイル:
        - logs/best_params.json（最適化済みハイパーパラメータ）
        - data/preprocessed_usdjpy_with_fundamental.csv（学習データ）
    - 出力ファイル:
        - logs/metaai_model_latest.zip（再学習済みモデル）
    """
    best_params_path = LOGS_DIR / "best_params.json"
    data_path = DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv"
    tensorboard_log_dir = LOGS_DIR / "ppo_tensorboard_logs"
    model_save_path = LOGS_DIR / "metaai_model_latest.zip"

    if not best_params_path.exists():
        logger.error(f"❌ 最適化結果が見つかりません: {best_params_path}")
        return

    try:
        with open(best_params_path, "r") as f:
            best_params = json.load(f)
        logger.info(f"📦 読み込まれた最適パラメータ: {best_params}")
    except Exception as e:
        logger.error(f"❌ パラメータ読み込みエラー: {e}")
        raise

    # ✅ 環境初期化
    try:
        env = TradingEnvWithFundamentals(str(data_path))
        logger.info("🌱 環境の初期化成功")
    except Exception as e:
        logger.error(f"❌ 環境初期化失敗: {e}")
        raise

    # ✅ PPOモデル再構築
    try:
        model = PPO(
            "MlpPolicy",
            env,
            learning_rate=best_params["learning_rate"],
            n_steps=best_params["n_steps"],
            gamma=best_params["gamma"],
            ent_coef=best_params["ent_coef"],
            verbose=0,
            tensorboard_log=str(tensorboard_log_dir),
        )
        logger.info("🛠 PPOモデル構築成功")
    except Exception as e:
        logger.error(f"❌ PPOモデル構築エラー: {e}")
        raise

    # ✅ 学習実行
    try:
        logger.info("⚙️ MetaAI: 再学習を開始します...")
        model.learn(total_timesteps=1000)
        logger.info("✅ 再学習完了")
    except Exception as e:
        logger.error(f"❌ モデル学習エラー: {e}")
        raise

    # ✅ モデル保存
    try:
        model.save(str(model_save_path))
        logger.info(f"📁 モデル保存完了: {model_save_path}")
    except Exception as e:
        logger.error(f"❌ モデル保存失敗: {e}")
        raise

def main():
    logger.info("👑 王Noctria: MetaAIに叡智を授ける儀を開始せよ")
    apply_best_params_to_metaai()
    logger.info("🌟 王国の進化が完了しました！MetaAIは新たな力を得ました。")

if __name__ == "__main__":
    main()
