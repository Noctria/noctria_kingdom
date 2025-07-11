#!/usr/bin/env python3
# coding: utf-8

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy

# Airflowのコンテキストから呼び出された場合、coreパッケージをインポート可能にする
import sys
import os
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

# 🏰 王国の叡智を記録する記録係
logger = setup_logger("metaai_apply_script", LOGS_DIR / "pdca" / "metaai_apply.log")

# ================================================
# ★改善点: DAGから直接呼び出されるメイン関数
# ================================================
def apply_best_params_to_metaai(
    best_params: Dict[str, Any],
    total_timesteps: int = 50000,
    n_eval_episodes: int = 20,
    model_version: str = None
) -> Dict[str, Any]:
    """
    ✅ MetaAIに最適パラメータを適用し再学習・評価・保存を行い、結果を返す
    
    引数:
        best_params (dict): Optunaが見つけた最適ハイパーパラメータ
        total_timesteps (int): 再学習時の総タイムステップ数
        n_eval_episodes (int): 最終評価のエピソード数
        model_version (str, optional): モデルのバージョン名。指定しない場合はタイムスタンプ。

    戻り値:
        dict: 保存されたモデルのパスと評価スコアを含む辞書
    """
    if not best_params:
        logger.error("❌ 最適化パラメータが提供されませんでした。処理を中断します。")
        raise ValueError("best_params cannot be None or empty.")

    logger.info(f"📦 受け取った最適パラメータ: {best_params}")

    # --- パス設定 ---
    data_path = MARKET_DATA_CSV
    tensorboard_log_dir = LOGS_DIR / "ppo_tensorboard_logs"
    
    # ★改善点: モデルのバージョン管理
    version = model_version if model_version else datetime.now().strftime("%Y%m%d-%H%M%S")
    model_save_path = MODELS_DIR / f"metaai_model_{version}.zip"
    latest_model_symlink = MODELS_DIR / "metaai_model_latest.zip"
    
    # --- 環境初期化 ---
    try:
        env = TradingEnvWithFundamentals(str(data_path))
        eval_env = TradingEnvWithFundamentals(str(data_path))
        logger.info("🌱 環境の初期化成功")
    except Exception as e:
        logger.error(f"❌ 環境初期化失敗: {e}", exc_info=True)
        raise

    # --- PPOモデル再構築 ---
    try:
        # PPOコンストラクタは **kwargs を受け付けるので、直接渡すのがクリーン
        model = PPO(
            "MlpPolicy",
            env,
            verbose=0,
            tensorboard_log=str(tensorboard_log_dir),
            **best_params
        )
        logger.info("🛠 PPOモデル構築成功")
    except Exception as e:
        logger.error(f"❌ PPOモデル構築エラー: {e}", exc_info=True)
        raise

    # --- 学習実行 ---
    try:
        logger.info(f"⚙️ MetaAI: 再学習を開始します... (Timesteps: {total_timesteps})")
        model.learn(total_timesteps=total_timesteps)
        logger.info("✅ 再学習完了")
    except Exception as e:
        logger.error(f"❌ モデル学習エラー: {e}", exc_info=True)
        raise

    # --- ★追加: 再学習後の最終評価 ---
    try:
        final_mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=n_eval_episodes)
        logger.info(f"🏆 再学習後モデルの最終評価スコア: {final_mean_reward:.4f}")
    except Exception as e:
        logger.error(f"❌ 最終評価エラー: {e}", exc_info=True)
        # 評価に失敗してもモデルは保存を試みる
        final_mean_reward = -9999.0

    # --- モデル保存 ---
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model.save(model_save_path)
        logger.info(f"📁 モデル保存完了: {model_save_path}")

        # 'latest'へのシンボリックリンクを更新
        if latest_model_symlink.is_symlink():
            latest_model_symlink.unlink()
        latest_model_symlink.symlink_to(model_save_path)
        logger.info(f"🔗 'latest'シンボリックリンクを更新しました -> {model_save_path.name}")

    except Exception as e:
        logger.error(f"❌ モデル保存失敗: {e}", exc_info=True)
        raise

    # ★改善点: 結果を辞書として返す (XComsで次に渡すため)
    result = {
        "model_path": str(model_save_path),
        "evaluation_score": final_mean_reward
    }
    return result

# ================================================
# CLI実行時（ローカルでのデバッグ用）
# ================================================
if __name__ == "__main__":
    logger.info("👑 王Noctria: MetaAIに叡智を授ける儀をCLIから開始せよ")
    
    # --- デバッグ用のダミーパラメータ ---
    mock_best_params = {
        'learning_rate': 0.0001,
        'n_steps': 1024,
        'gamma': 0.99,
        'ent_coef': 0.01,
        'clip_range': 0.2
    }
    
    # --- テスト実行 ---
    result_info = apply_best_params_to_metaai(
        best_params=mock_best_params,
        total_timesteps=1000, # テストなので小さく
        n_eval_episodes=2
    )
    
    logger.info(f"🌟 王国の進化が完了しました！MetaAIは新たな力を得ました。結果: {result_info}")
