#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import json
import optuna
from functools import partial

# Airflow & CLI 両対応の import 解決
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

# ✅ ロガー定義（共通）
logger = setup_logger("optimize_script", LOGS_DIR / "pdca" / "optimize.log")


# ================================================
# 🎯 Optuna 目的関数（重い import はここで）
# ================================================
def objective(trial: optuna.Trial, total_timesteps: int, n_eval_episodes: int) -> float:
    logger.info(f"🎯 試行 {trial.number} を開始")

    # ✅ 遅延 import（Airflow DAGスキャン対策）
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import EvalCallback
    from stable_baselines3.common.evaluation import evaluate_policy
    # ❗️【修正点】正しいimportパスに修正
    from sb3_contrib.optuna import OptunaPruner

    # ハイパーパラメータ空間の定義
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

    pruner_callback = OptunaPruner(trial, eval_env, n_eval_episodes=n_eval_episodes)
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=None,
        log_path=None,
        eval_freq=max(total_timesteps // 5, 1),
        deterministic=True,
        render=False,
        callback_on_new_best=pruner_callback
    )

    try:
        model.learn(total_timesteps=total_timesteps, callback=eval_callback)
        mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=n_eval_episodes)
        logger.info(f"✅ 最終評価: 平均報酬 = {mean_reward:.2f}")
        return mean_reward
    except (AssertionError, ValueError) as e:
        logger.warning(f"⚠️ 学習中のエラーでプルーニング: {e}")
        raise optuna.exceptions.TrialPruned()
    except Exception as e:
        logger.error(f"❌ 学習・評価中の致命的エラー: {e}", exc_info=True)
        raise


# ================================================
# 🚀 DAG / CLI 用メイン関数
# ================================================
def optimize_main(n_trials: int = 10, total_timesteps: int = 20000, n_eval_episodes: int = 10):
    from optuna.integration.skopt import SkoptSampler
    from optuna.pruners import MedianPruner

    study_name = "noctria_meta_ai_ppo"
    storage = os.getenv("OPTUNA_DB_URL")
    if not storage:
        db_path = DATA_DIR / 'optuna_studies.db'
        storage = f"sqlite:///{db_path}"
        logger.warning(f"⚠️ OPTUNA_DB_URLが未設定です。ローカルDBを使用します: {storage}")

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

        objective_with_params = partial(
            objective,
            total_timesteps=total_timesteps,
            n_eval_episodes=n_eval_episodes
        )

        study.optimize(objective_with_params, n_trials=n_trials, timeout=3600)

    except Exception as e:
        logger.error(f"❌ Optuna最適化でエラー発生: {e}", exc_info=True)
        return None

    logger.info("👑 最適化完了！")
    logger.info(f"  - Trial: {study.best_trial.number}")
    logger.info(f"  - Score: {study.best_value:.4f}")
    logger.info(f"  - Params: {json.dumps(study.best_params, indent=2)}")
    return study.best_params


# ================================================
# 🧪 CLI デバッグ用
# ================================================
if __name__ == "__main__":
    logger.info("🧪 CLI: テスト実行中")
    best_params = optimize_main(n_trials=5, total_timesteps=1000, n_eval_episodes=2)

    if best_params:
        best_params_file = LOGS_DIR / "best_params_local_test.json"
        with open(best_params_file, "w") as f:
            json.dump(best_params, f, indent=2)
        logger.info(f"📁 保存完了: {best_params_file}")
