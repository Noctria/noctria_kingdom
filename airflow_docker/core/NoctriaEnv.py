import numpy as np
import pandas as pd
from typing import Tuple

class NoctriaEnv:
    """
    シンプルなNoctria環境シミュレーター。
    状態空間はランダム、報酬は勝率ベースで評価される。
    """

    def __init__(self, max_steps: int = 10, state_dim: int = 12, verbose: bool = False):
        self.max_steps = max_steps
        self.state_dim = state_dim
        self.action_space = [-1, 0, 1]  # SELL, HOLD, BUY
        self.verbose = verbose

        self.current_step = 0
        self.trade_history = self._generate_dummy_history()

    def reset(self) -> np.ndarray:
        self.current_step = 0
        self.trade_history = self._generate_dummy_history()
        return self._get_state()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        self.current_step += 1
        reward = self._calculate_reward(action)
        done = self.current_step >= self.max_steps
        next_state = self._get_state()

        if self.verbose:
            print(f"[Step {self.current_step}] Action: {action}, Reward: {reward:.3f}")

        return next_state, reward, done, {}

    def _get_state(self) -> np.ndarray:
        return np.random.rand(self.state_dim)

    def _calculate_reward(self, action: int) -> float:
        total_trades = len(self.trade_history)
        wins = (self.trade_history["profit"] > 0).sum()
        win_rate = wins / total_trades if total_trades > 0 else 0.0

        # HOLD時はペナルティなし、トレード時は-0.05のコストを想定
        return win_rate - 0.05 if action != 0 else win_rate

    def _generate_dummy_history(self) -> pd.DataFrame:
        profits = np.random.choice([10, -5, 15, -7, 20, -10, 5, -2, 12, -3], size=self.max_steps)
        return pd.DataFrame({"profit": profits})
