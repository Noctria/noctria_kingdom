import numpy as np
import pandas as pd
import random

class NoctriaEnv:
    """
    簡易版 Noctria 環境（強化学習用）
    - 状態: 取引履歴から作った特徴量
    - 行動: 例として BUY(1), SELL(-1), HOLD(0)
    - 報酬: 週次勝率（例として）
    """

    def __init__(self):
        self.current_step = 0
        self.max_steps = 10  # 例: 10エピソードで終わる
        self.state_dim = 12  # 12次元の特徴量ベクトル
        self.action_space = [-1, 0, 1]  # SELL, HOLD, BUY

        # ダミーの取引履歴データ
        self.trade_history = pd.DataFrame({
            "profit": [10, -5, 15, -7, 20, -10, 5, -2, 12, -3]
        })

    def reset(self):
        self.current_step = 0
        state = self._get_state()
        return state

    def step(self, action):
        """
        action: -1 (SELL), 0 (HOLD), 1 (BUY)
        """
        self.current_step += 1

        # 報酬: 週次勝率を例にする
        total_trades = len(self.trade_history)
        wins = self.trade_history[self.trade_history["profit"] > 0].shape[0]
        win_rate = wins / total_trades if total_trades > 0 else 0

        # 例: 取引行動にペナルティを加味（無理に動くとマイナス）
        if action != 0:
            reward = win_rate - 0.05  # 動いた分だけ手数料的ペナルティ
        else:
            reward = win_rate

        # 簡単に done 条件
        done = self.current_step >= self.max_steps

        # 次状態はランダムな特徴量で例示
        next_state = self._get_state()

        info = {}
        return next_state, reward, done, info

    def _get_state(self):
        """
        例: 12次元のランダムな観測ベクトルを返す
        """
        return np.random.rand(self.state_dim)
