#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import json
import optuna
from functools import partial

# Airflowのコンテキストから呼び出された場合、coreパッケージをインポート可能にする
# このスクリプトを単体で実行する場合は、プロジェクトルートをPYTHONPATHに追加する必要がある
try:
    from core.path_config import *
    from core.logger import setup_logger
    from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals
except ImportError:
    # プロジェクトルートからの相対パスを解決
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from core.path_config import *
    from core.logger import setup_logger
    from core.meta_ai_env_with_fundamentals import TradingEnvWithFundamentals

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback
from optuna.integration.skopt import SkoptSampler
from optuna.pruners import MedianPruner
from optuna.integration import TensorBoardCallback as OptunaTensorBoardCallback # OptunaのTensorBoardCallback
from optuna_integration.sb3 import TrialPruningCallback # ★正しいパス: `optuna_integration`から直接インポート

# ✅ 王国記録係（ログ）を召喚
logger = setup_logger("optimize_script", LOGS_DIR / "pdca" / "optimize.log")

# ================================================
# Optuna 目的関数
# ★改善点: Pruningを有効にするため、引数に trial を受け取る
# ================================================
def objective(trial: optuna.Trial, total_timesteps: int, n_eval_episodes: int) -> float:
    logger.info(f"🎯 試行 {trial.number} を開始")

    # --- ハイパーパラメータの探索空間を定義 ---
    params = {
        'learning_rate': trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True),
        'n_steps': trial.suggest_int('n_steps', 128, 2048, step=128),
        'gamma': trial.suggest_float('gamma', 0.9, 0.9999),
        'ent_coef': trial.suggest_float('ent_coef', 0.0, 0.1),
        'clip_range': trial.suggest_float('clip_range', 0.1, 0.4),
    }
    logger.info(f"🔧 探索パラメータ: {params}")

    # --- 環境とモデルのセットアップ ---
    try:
        # 環境は各トライアルで新しく作成
        env = TradingEnvWithFundamentals(MARKET_DATA_CSV)
        eval_env = TradingEnvWithFundamentals(MARKET_DATA_CSV) # 評価用環境
        
        model = PPO("MlpPolicy", env, **params, verbose=0)
    except Exception as e:
        logger.error(f"❌ 環境またはモデルの初期化失敗: {e}", exc_info=True)
        raise optuna.exceptions.TrialPruned() # エラー時はプルーニング扱い

    # --- Pruning用コールバックのセットアップ ---
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=None, # DAG実行中はモデルを保存しない
        log_path=None, # DAG実行中はログを保存しない
        eval_freq=max(total_timesteps // 5, 1), # 5回に分けて評価
        deterministic=True,
        render=False,
        callback_after_eval=TrialPruningCallback(trial, "mean_reward") # ★追加
    )

    # --- 学習と評価 ---
    try:
        model.learn(total_timesteps=total_timesteps, callback=eval_callback)
        mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=n_eval_episodes)
        logger.info(f"✅ 最終評価結果（平均報酬）: {mean_reward}")
        return mean_reward
    except (AssertionError, ValueError) as e:
        logger.warning(f"⚠️ 学習中にエラーが発生し、試行をプルーニングします: {e}")
        raise optuna.exceptions.TrialPruned()
    except Exception as e:
        logger.error(f"❌ モデル学習または評価で致命的なエラー: {e}", exc_info=True)
        raise

# ================================================
# DAGや他スクリプトから呼べるメイン関数
# ★改善点: Airflow DAGと連携しやすく修正
# ================================================
def optimize_main(n_trials: int = 20, total_timesteps: int = 20000, n_eval_episodes: int = 10):
    """Optunaによるハイパーパラメータ最適化を実行し、最適なパラメータを返す"""
    
    study_name = "noctria_meta_ai_ppo"
    storage = os.getenv("OPTUNA_DB_URL", f"sqlite:///{DATA_DIR / 'optuna_studies.db'}")

    logger.info(f"📚 Optuna Study開始: {study_name} (試行回数: {n_trials})")
    logger.info(f"🔌 Storage: {storage}")

    try:
        # サンプラーとプルーナーでより賢く探索
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

        # objective関数に固定引数を渡すためにfunctools.partialを使用
        objective_with_params = partial(
            objective,
            total_timesteps=total_timesteps,
            n_eval_episodes=n_eval_episodes
        )

        study.optimize(objective_with_params, n_trials=n_trials, timeout=3600) # 1時間でタイムアウト
        
    except Exception as e:
        logger.error(f"❌ Optuna最適化プロセス全体でエラー: {e}", exc_info=True)
        return None # エラー時はNoneを返す

    logger.info("👑 最適化完了！")
    logger.info(f"   - 最良試行: trial {study.best_trial.number}")
    logger.info(f"   - 最高スコア: {study.best_value:.4f}")
    logger.info(f"   - 最適パラメータ: {study.best_params}")

    # ★改善点: 結果をファイル保存せず、辞書として返す
    return study.best_params

# ================================================
# CLI実行時（ローカルでのデバッグ用）
# ================================================
if __name__ == "__main__":
    logger.info("CLIからデバッグ実行します。")
    # 小さな設定でテスト実行
    best_params = optimize_main(n_trials=5, total_timesteps=1000, n_eval_episodes=2)
    
    if best_params:
        # 結果をローカルファイルに保存して確認
        best_params_file = LOGS_DIR / "best_params_local_test.json"
        with open(best_params_file, "w") as f:
            json.dump(best_params, f, indent=2)
        logger.info(f"📁 テスト実行の最適パラメータを保存しました: {best_params_file}")
