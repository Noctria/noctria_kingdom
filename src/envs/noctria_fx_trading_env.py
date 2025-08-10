import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Optional, Dict, Any, Tuple

class NoctriaFXTradingEnv(gym.Env):
    """
    最小テンプレ（必要に応じて置き換えOK）
    - 観測: 連続10次元
    - 行動: 3（0:SELL / 1:HOLD / 2:BUY）
    - 報酬: ダミー（手数料控除つきランダム）
    """
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        window: int = 64,
        fee: float = 0.0002,
        reward_mode: str = "pnl",
        render_mode: Optional[str] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ):
        super().__init__()
        self.window = int(window)
        self.fee = float(fee)
        self.reward_mode = str(reward_mode)
        self.render_mode = render_mode

        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(10,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)

        self._rng = np.random.default_rng(seed)
        self._state = np.zeros(10, dtype=np.float32)

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._state = self._rng.normal(0, 0.1, size=(10,)).astype(np.float32)
        return self._state, {}

    def step(self, action: int):
        assert self.action_space.contains(action), f"invalid action {action}"
        # ダミー遷移
        self._state += self._rng.normal(0, 0.05, size=(10,)).astype(np.float32)

        # ダミー報酬（本番はPnL等へ差し替え）
        base = 0.1 if action == 2 else (0.0 if action == 1 else -0.05)
        reward = float(self._rng.normal(base, 0.1))
        if action in (0, 2):
            reward -= self.fee

        terminated = False
        truncated = False
        return self._state, reward, terminated, truncated, {}

    def render(self):
        pass

    def close(self):
        pass
