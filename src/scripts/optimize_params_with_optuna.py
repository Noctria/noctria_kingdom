#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import json
import optuna
from functools import partial

# Airflowのコンテキストから呼び出された場合、coreパッケージをインポート可能にする
try:
    from core.path_config import *
    from core.logger import setup_logger
    from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
except ImportError:
    # 単体実行用：プロジェクトルートを追加
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from core.path_config import *
    from core.logger import setup_logger
    from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.evaluation import evaluate_policy  # ✅ 評価関数のインポート
from optuna.integration.skopt import SkoptSampler
from optuna.pruners import MedianPruner
from optuna.integration import TensorBoardCallback as OptunaTensorBoardCallback

# ✅ 修正: sb3-contrib による Optuna Pruning Callback
from sb3_contrib.common.optuna_callback import TrialEvalCallback

# ✅ ロガー
logger = setup_logger("optimize_script", LOGS_DIR / "pdca" / "optimize.log")


# ================================================
# 🎯 Optuna 目的関数
# ================================================
def objective(trial: optuna.Trial, total_timesteps: int, n_eval_episodes: int) -> float:
    logger.info(f"🎯 試行 {trial.number} を開始")

    params = {
        'learning_rate': trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True),
        'n_steps': trial.suggest_int('n_steps', 128, 2048, step=128),
        'gamma': trial.suggest_float('gamma', 0.9, 0.9999),
        'ent_coef': trial.suggest_float('ent_coef', 0.0, 0.1),
        'clip_range': trial.suggest_float('clip_range', 0.1, 0.4),
    }
    logger.info(f"🔧 探索パラメータ: {params}")

    try:
        env = TradingEnvWithFundamentals(MARKET_DATA_CSV)
        eval_env = TradingEnvWithFundamentals(MARKET_DATA_CSV)
        model = PPO("MlpPolicy", env, **params, verbose=0)
    except Exception as e:
        logger.error(f"❌ モデル初期化失敗: {e}", exc_info=True)
        raise optuna.exceptions.TrialPruned()

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=None,
        log_path=None,
        eval_freq=max(total_timesteps // 5, 1),
        deterministic=True,
        render=False,
        callback_after_eval=TrialEvalCallback(trial, eval_env, n_eval_episodes, deterministic=True)
    )

    try:
        model.learn(total_timesteps=total_timesteps, callback=eval_callback)
        mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=n_eval_episodes)
        logger.info(f"✅ 最終評価結果: 平均報酬 = {mean_reward:.2f}")
        return mean_reward
    except (AssertionError, ValueError) as e:
        logger.warning(f"⚠️ 学習中のエラーによりプルーニング: {e}")
        raise optuna.exceptions.TrialPruned()
    except Exception as e:
        logger.error(f"❌ 致命的なエラー: {e}", exc_info=True)
        raise


# ================================================
# 🚀 DAG連携用エントリポイント
# ================================================
def optimize_main(n_trials: int = 20, total_timesteps: int = 20000, n_eval_episodes: int = 10):
    study_name = "noctria_meta_ai_ppo"
    storage = os.getenv("OPTUNA_DB_URL", f"sqlite:///{DATA_DIR / 'optuna_studies.db'}")

    logger.info(f"📚 Optuna Study開始: {study_name}")
    logger.info(f"🔌 Storage: {storage}")

    try:
        sampler = SkoptSampler(skopt_kwargs={'base_estimator': 'GP', 'acq_func': 'EI'})
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=total_timesteps // 3)

        study = optuna.create_study(
            direction="maximize",
            study_name=study_name,
            storage=storage,
            sampler=sampler,
            pruner=pruner,
            load_if_exists=True
        )

        objective_with_params = partial(objective,
                                        total_timesteps=total_timesteps,
                                        n_eval_episodes=n_eval_episodes)

        study.optimize(objective_with_params, n_trials=n_trials, timeout=3600)

    except Exception as e:
        logger.error(f"❌ 最適化全体でエラー: {e}", exc_info=True)
        return None

    logger.info("👑 最適化完了！")
    logger.info(f"   - 最良試行: trial {study.best_trial.number}")
    logger.info(f"   - 最高スコア: {study.best_value:.4f}")
    logger.info(f"   - 最適パラメータ: {study.best_params}")

    return study.best_params


# ================================================
# 🧪 CLI デバッグ用エントリポイント
# ================================================
if __name__ == "__main__":
    logger.info("CLIからテスト実行を開始します。")
    best_params = optimize_main(n_trials=5, total_timesteps=1000, n_eval_episodes=2)

    if best_params:
        best_params_file = LOGS_DIR / "best_params_local_test.json"
        with open(best_params_file, "w") as f:
            json.dump(best_params, f, indent=2)
        logger.info(f"📁 テスト結果を保存: {best_params_file}")
