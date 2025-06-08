import numpy as np
import pandas as pd

class NoctriaEnv:
    def __init__(self):
        self.current_step = 0
        self.max_steps = 10
        self.state_dim = 12
        self.action_space = [-1, 0, 1]  # SELL, HOLD, BUY

        self.trade_history = pd.DataFrame({
            "profit": [10, -5, 15, -7, 20, -10, 5, -2, 12, -3]
        })

    def reset(self):
        self.current_step = 0
        return self._get_state()

    def step(self, action):
        self.current_step += 1
        total_trades = len(self.trade_history)
        wins = self.trade_history[self.trade_history["profit"] > 0].shape[0]
        win_rate = wins / total_trades if total_trades > 0 else 0

        reward = win_rate - 0.05 if action != 0 else win_rate
        done = self.current_step >= self.max_steps
        next_state = self._get_state()
        return next_state, reward, done, {}

    def _get_state(self):
        return np.random.rand(self.state_dim)
