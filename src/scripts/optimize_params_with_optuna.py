#!/usr/bin/env python3
# coding: utf-8

"""
Noctria Kingdom - Optuna Hyperparameter Optimization (PPO)
- Gymnasium API 準拠の環境を Monitor で包み、DummyVecEnv で学習/評価を安定化
- Optuna のプルーニングを EvalCallback タイミングで実施
- Airflow / 直実行 の両対応で import を堅牢化
"""

from __future__ import annotations

import os
import sys
import json
from functools import partial
from typing import Any

import optuna

# ===== Airflow & CLI 両対応の import 解決（src. に統一） =====
try:
    from src.core.path_config import LOGS_DIR, DATA_DIR, MARKET_DATA_CSV
    from src.core.logger import setup_logger
    from src.core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
except Exception:
    # 旧起動/相対実行のフォールバック
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from src.core.path_config import LOGS_DIR, DATA_DIR, MARKET_DATA_CSV  # type: ignore
    from src.core.logger import setup_logger  # type: ignore
    from src.core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals  # type: ignore

LOGS_DIR.mkdir(parents=True, exist_ok=True)
logger = setup_logger("optimize_script", LOGS_DIR / "pdca" / "optimize.log")


# ======================================================
# 🎯 Optuna用 Pruning Callback（EvalCallbackを拡張）
#   * 評価のたびに last_mean_reward を中間値として報告
# ======================================================
from stable_baselines3.common.callbacks import EvalCallback

class OptunaPruningCallback(EvalCallback):
    def __init__(self, eval_env, trial: optuna.Trial, n_eval_episodes=5, eval_freq=1000, verbose=0):
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
        # 親で評価実行（必要タイミングで evaluate() が呼ばれる）
        cont = super()._on_step()
        # 評価が走った回は last_mean_reward が更新される
        if (self.n_calls % self.eval_freq == 0) and (self.last_mean_reward is not None):
            intermediate_value = float(self.last_mean_reward)
            # ステップ数を「中間ステップ」として報告
            self.trial.report(intermediate_value, step=self.n_calls)
            if self.trial.should_prune():
                logger.info(f"⏩ Trial pruned at step={self.n_calls}, reward={intermediate_value:.4f}")
                self.is_pruned = True
                return False  # → 学習停止（プルーニング）
        return cont


# ======================================================
# 🎯 Optuna 目的関数
#   * Monitor + DummyVecEnv で包む
#   * 評価は return_episode_rewards=True でデバッグ性UP
# ======================================================
def objective(trial: optuna.Trial, total_timesteps: int, n_eval_episodes: int) -> float:
    logger.info(f"🎯 試行 {trial.number} を開始")

    from stable_baselines3 import PPO
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv
    from stable_baselines3.common.evaluation import evaluate_policy

    # ハイパーパラメータ空間
    params = {
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "n_steps": trial.suggest_int("n_steps", 128, 2048, step=128),
        "gamma": trial.suggest_float("gamma", 0.9, 0.9999),
        "ent_coef": trial.suggest_float("ent_coef", 0.0, 0.1),
        "clip_range": trial.suggest_float("clip_range", 0.1, 0.4),
        # 必要に応じて追加
    }
    logger.info(f"🔧 探索パラメータ: {params}")

    # --- 環境生成（Monitor で包んでから VecEnv 化） ---
    def make_env():
        env = TradingEnvWithFundamentals(str(MARKET_DATA_CSV))
        return Monitor(env)  # SB3 推奨のモニター

    try:
        env = DummyVecEnv([make_env])       # 学習用
        eval_env = DummyVecEnv([make_env])  # 評価用
        model = PPO("MlpPolicy", env, **params, verbose=0)
    except Exception as e:
        logger.error(f"❌ モデル初期化失敗: {e}", exc_info=True)
        raise optuna.TrialPruned()

    # 評価間隔は総ステップの 1/5 を目安
    eval_freq = max(total_timesteps // 5, 1)
    pruning_cb = OptunaPruningCallback(
        eval_env=eval_env,
        trial=trial,
        n_eval_episodes=n_eval_episodes,
        eval_freq=eval_freq,
        verbose=0,
    )

    # --- 学習 ---
    try:
        model.learn(total_timesteps=total_timesteps, callback=pruning_cb)
        if pruning_cb.is_pruned:
            # 上で False を返して学習停止 → ここで明示的に伝える
            raise optuna.TrialPruned()

        # --- 評価（詳細ログ） ---
        mean_reward, ep_rewards = evaluate_policy(
            model,
            eval_env,
            n_eval_episodes=n_eval_episodes,
            return_episode_rewards=True,
            deterministic=True,
        )
        logger.info(f"[DEBUG] ep_returns={ep_rewards}, n={len(ep_rewards)}")
        logger.info(f"✅ 最終評価: 平均報酬 = {mean_reward:.2f}")

        return float(mean_reward)

    except (AssertionError, ValueError) as e:
        # Gym/Gymnasium 不整合などはプルーニングで早期終了
        logger.warning(f"⚠️ 学習中のエラーでプルーニング: {e}")
        raise optuna.TrialPruned()
    except optuna.TrialPruned:
        logger.info("⏩ プルーニング判定により中断")
        raise
    except Exception as e:
        logger.error(f"❌ 学習・評価中の致命的エラー: {e}", exc_info=True)
        # ここは “失敗” 扱いにしておく（再現のため raise）
        raise
    finally:
        try:
            env.close()
            eval_env.close()
        except Exception:
            pass


# ======================================================
# 🚀 DAG / CLI 用メイン関数
# ======================================================
def optimize_main(n_trials: int = 10, total_timesteps: int = 20_000, n_eval_episodes: int = 10) -> dict[str, Any] | None:
    from optuna.integration.skopt import SkoptSampler
    from optuna.pruners import MedianPruner

    study_name = "noctria_meta_ai_ppo"
    storage = os.getenv("OPTUNA_DB_URL")
    if not storage:
        # ローカル SQLite（Airflow無しのローカル実行でも動く）
        db_path = DATA_DIR / "optuna_studies.db"
        storage = f"sqlite:///{db_path}"
        logger.warning(f"⚠️ OPTUNA_DB_URL 未設定のためローカルDBを使用: {storage}")

    logger.info(f"📚 Optuna Study開始: {study_name}")
    logger.info(f"🔌 Storage: {storage}")

    try:
        sampler = SkoptSampler(skopt_kwargs={"base_estimator": "GP", "acq_func": "EI"})
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=max(total_timesteps // 3, 1))

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

        # timeout は必要なら調整
        study.optimize(objective_with_params, n_trials=n_trials, timeout=None)

    except optuna.TrialPruned:
        # 直近で prune された場合
        logger.info("⏩ 直近 Trial がプルーニングで終了")
    except Exception as e:
        logger.error(f"❌ Optuna最適化でエラー発生: {e}", exc_info=True)
        return None

    if len(study.trials) == 0 or study.best_trial is None:
        logger.warning("⚠️ 有効な Trial がありませんでした。")
        return None

    logger.info("👑 最適化完了！")
    logger.info(f"  - Trial: {study.best_trial.number}")
    logger.info(f"  - Score: {study.best_value:.4f}")
    logger.info(f"  - Params: {json.dumps(study.best_params, indent=2)}")
    return study.best_params


# ======================================================
# 🧪 CLI デバッグ用
# ======================================================
if __name__ == "__main__":
    logger.info("🧪 CLI: テスト実行開始")
    best_params = optimize_main(n_trials=5, total_timesteps=2_000, n_eval_episodes=5)

    if best_params:
        best_params_file = LOGS_DIR / "pdca" / "best_params_local_test.json"
        best_params_file.parent.mkdir(parents=True, exist_ok=True)
        with open(best_params_file, "w", encoding="utf-8") as f:
            json.dump(best_params, f, indent=2, ensure_ascii=False)
        logger.info(f"📁 保存完了: {best_params_file}")
    else:
        logger.info("（best_params は得られませんでした）")
