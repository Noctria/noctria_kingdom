#!/usr/bin/env python3
# coding: utf-8

"""
Optuna + SB3(PPO) ハイパラ探索ランナー（修正版）
- Gymnasium 互換 (SB3 v2.x)
- 監視: Monitor を env / eval_env に挿入
- 評価: evaluate_policy でエピソード報酬ログ
- Airflow 実行＆CLI 直叩きに両対応
"""

import os
import sys
import json
import optuna
from functools import partial

# ===== Robust import (src.core 優先 → core フォールバック) =====
try:
    from src.core.path_config import *        # noqa
    from src.core.logger import setup_logger  # noqa
    from src.core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals  # noqa
except Exception:
    # 直接実行などで src が解決できない場合に備える
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from core.path_config import *        # type: ignore  # noqa
    from core.logger import setup_logger  # type: ignore  # noqa
    from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals  # type: ignore  # noqa

from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback

# ロガー
logger = setup_logger("optimize_script", LOGS_DIR / "pdca" / "optimize.log")


# ======================================================
# 🎯 Optuna用 PruningCallback (SB3 EvalCallback 拡張)
#   - super()._on_step() の評価後に last_mean_reward を参照
# ======================================================
class OptunaPruningCallback(EvalCallback):
    def __init__(self, eval_env, trial, n_eval_episodes=5, eval_freq=1000, verbose=0):
        super().__init__(
            eval_env=eval_env,
            best_model_save_path=None,
            log_path=None,
            eval_freq=eval_freq,
            n_eval_episodes=n_eval_episodes,
            deterministic=True,
            render=False,
            verbose=verbose,
        )
        self.trial = trial
        self.is_pruned = False

    def _on_step(self) -> bool:
        # 親クラスが適切なタイミングで評価を走らせ、last_mean_reward を更新する
        continue_training = super()._on_step()
        # 評価タイミングのみ prune 判定
        if self.n_calls % self.eval_freq == 0 and self.last_mean_reward is not None:
            intermediate_value = float(self.last_mean_reward)
            self.trial.report(intermediate_value, step=self.n_calls)
            if self.trial.should_prune():
                logger.info(f"⏩ Trial pruned at step={self.n_calls} reward={intermediate_value:.4f}")
                self.is_pruned = True
                return False
        return continue_training


# ======================================================
# 🧰 環境ユーティリティ
# ======================================================
def make_env(csv_path) -> Monitor:
    """
    TradingEnv を構築し、Monitor でラップして返す。
    Gymnasium 署名（reset/step）に準拠した env であることが前提。
    """
    env = TradingEnvWithFundamentals(str(csv_path))
    return Monitor(env)


# ======================================================
# 🎯 Optuna 目的関数
# ======================================================
def objective(trial: optuna.Trial, total_timesteps: int, n_eval_episodes: int) -> float:
    logger.info(f"🎯 試行 {trial.number} を開始")

    from stable_baselines3 import PPO
    from stable_baselines3.common.evaluation import evaluate_policy

    # ハイパーパラメータ探索空間
    params = {
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "n_steps": trial.suggest_int("n_steps", 128, 2048, step=128),
        "gamma": trial.suggest_float("gamma", 0.90, 0.9999),
        "ent_coef": trial.suggest_float("ent_coef", 0.0, 0.1),
        "clip_range": trial.suggest_float("clip_range", 0.1, 0.4),
    }
    logger.info(f"🔧 探索パラメータ: {params}")

    # 環境構築（Monitor を必ず噛ませる）
    try:
        env = make_env(MARKET_DATA_CSV)
        eval_env = make_env(MARKET_DATA_CSV)
        model = PPO("MlpPolicy", env, **params, verbose=0)
    except Exception as e:
        logger.error(f"❌ モデル/環境初期化失敗: {e}", exc_info=True)
        # 初期化で失敗した試行は prune 扱いに
        raise optuna.TrialPruned()

    # 評価頻度：全体の 1/5 ごと（最低1）
    eval_freq = max(total_timesteps // 5, 1)
    pruning_cb = OptunaPruningCallback(
        eval_env=eval_env,
        trial=trial,
        n_eval_episodes=n_eval_episodes,
        eval_freq=eval_freq,
        verbose=0,
    )

    try:
        model.learn(total_timesteps=total_timesteps, callback=pruning_cb)
        if pruning_cb.is_pruned:
            raise optuna.TrialPruned()

        # 最終評価（デバッグとして各エピソード報酬も記録）
        # SB3 v2: return_episode_rewards=True で (ep_returns, ep_lengths)
        ep_returns, ep_lengths = None, None
        try:
            ep_returns, ep_lengths = evaluate_policy(
                model,
                eval_env,
                n_eval_episodes=n_eval_episodes,
                return_episode_rewards=True,
            )
            logger.info(f"[DEBUG] ep_returns={ep_returns}, ep_lengths={ep_lengths}")
            mean_reward = float(sum(ep_returns) / max(len(ep_returns), 1))
        except TypeError:
            # 旧型式の戻り値（mean, std）にフォールバック
            mean_reward, _ = evaluate_policy(
                model,
                eval_env,
                n_eval_episodes=n_eval_episodes,
                return_episode_rewards=False,
            )
            mean_reward = float(mean_reward)

        logger.info(f"✅ 最終評価: 平均報酬 = {mean_reward:.2f}")
        return float(mean_reward)

    except (AssertionError, ValueError) as e:
        # 学習中/評価中の一時的な失敗は prune
        logger.warning(f"⚠️ 学習中のエラーでプルーニング: {e}")
        raise optuna.TrialPruned()
    except optuna.TrialPruned:
        logger.info("⏩ プルーニング判定により中断")
        raise
    except Exception as e:
        logger.error(f"❌ 学習・評価中の致命的エラー: {e}", exc_info=True)
        raise
    finally:
        try:
            env.close()
            eval_env.close()
        except Exception:
            pass
        del model


# ======================================================
# 🚀 DAG / CLI 用メイン関数
# ======================================================
def optimize_main(n_trials: int = 10, total_timesteps: int = 20_000, n_eval_episodes: int = 10):
    from optuna.integration.skopt import SkoptSampler
    from optuna.pruners import MedianPruner

    study_name = "noctria_meta_ai_ppo"
    storage = os.getenv("OPTUNA_DB_URL")
    if not storage:
        db_path = DATA_DIR / "optuna_studies.db"
        storage = f"sqlite:///{db_path}"
        logger.warning(f"⚠️ OPTUNA_DB_URL が未設定です。ローカルDBを使用します: {storage}")

    logger.info(f"📚 Optuna Study開始: {study_name}")
    logger.info(f"🔌 Storage: {storage}")

    try:
        sampler = SkoptSampler(skopt_kwargs={"base_estimator": "GP", "acq_func": "EI"})
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=total_timesteps // 3)

        study = optuna.create_study(
            direction="maximize",
            study_name=study_name,
            storage=storage,
            sampler=sampler,
            pruner=pruner,
            load_if_exists=True,
        )

        objective_with_params = partial(
            objective,
            total_timesteps=total_timesteps,
            n_eval_episodes=n_eval_episodes,
        )

        # timeout は必要に応じて調整
        study.optimize(objective_with_params, n_trials=n_trials, timeout=3600)

    except Exception as e:
        logger.error(f"❌ Optuna最適化でエラー発生: {e}", exc_info=True)
        return None

    logger.info("👑 最適化完了！")
    logger.info(f"  - Trial: {study.best_trial.number}")
    logger.info(f"  - Score: {float(study.best_value):.4f}")
    logger.info(f"  - Params: {json.dumps(study.best_params, indent=2)}")
    return study.best_params


# ======================================================
# 🧪 CLI デバッグ用
# ======================================================
if __name__ == "__main__":
    logger.info("🧪 CLI: テスト実行中")
    best_params = optimize_main(n_trials=5, total_timesteps=1_000, n_eval_episodes=2)

    if best_params:
        best_params_file = LOGS_DIR / "best_params_local_test.json"
        best_params_file.parent.mkdir(parents=True, exist_ok=True)
        with open(best_params_file, "w", encoding="utf-8") as f:
            json.dump(best_params, f, indent=2, ensure_ascii=False)
        logger.info(f"📁 保存完了: {best_params_file}")
