# src/envs/noctria_fx_trading_env.py
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Optional, Dict, Any, Tuple

class NoctriaFXTradingEnv(gym.Env):
    """
    最小テンプレ（SB3推論互換）
    - 観測: 連続6次元（SB3保存済みモデル: Box(-inf, inf, (6,), float32) に合わせる）
    - 行動: Discrete(3) = {0: SELL, 1: HOLD, 2: BUY}  ※学習時の割当と揃えること
    - 報酬: ダミー（手数料控除つきランダム）
    - エピソード: max_episode_steps 到達で truncated=True
    """
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        window: int = 64,
        fee: float = 0.0002,
        reward_mode: str = "pnl",
        max_episode_steps: int = 200,
        render_mode: Optional[str] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ):
        super().__init__()
        self.window = int(window)
        self.fee = float(fee)
        self.reward_mode = str(reward_mode)
        self.max_episode_steps = int(max_episode_steps)
        self.render_mode = render_mode

        # ★ SB3モデルに合わせて 6 次元固定
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(6,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(3)  # 0:SELL / 1:HOLD / 2:BUY

        self._rng = np.random.default_rng(seed)
        self._state = np.zeros(6, dtype=np.float32)
        self._t = 0

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        # 観測は常に (6,) float32
        self._state = self._rng.normal(0, 0.1, size=(6,)).astype(np.float32)
        self._t = 0
        info: Dict[str, Any] = {}
        return self._state, info

    def step(self, action: int):
        assert self.action_space.contains(action), f"invalid action {action}"

        # ダミー遷移（数値安定化）
        self._state = (self._state + self._rng.normal(0, 0.05, size=(6,))).astype(np.float32)
        self._state = np.nan_to_num(self._state, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

        # ダミー報酬（本番はPnL等へ差し替え）
        # 例: BUY(2) ややプラス、HOLD(1) ニュートラル、SELL(0) ややマイナス
        base = 0.1 if action == 2 else (0.0 if action == 1 else -0.05)
        reward = float(self._rng.normal(base, 0.1))
        if action in (0, 2):
            reward -= self.fee
        reward = float(np.nan_to_num(reward, nan=0.0, posinf=0.0, neginf=0.0))

        self._t += 1
        terminated = False
        truncated = self._t >= self.max_episode_steps

        info: Dict[str, Any] = {}
        return self._state, reward, terminated, truncated, info

    def render(self):
        pass

    def close(self):
        pass
