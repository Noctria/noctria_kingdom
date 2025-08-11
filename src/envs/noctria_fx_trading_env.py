# src/envs/noctria_fx_trading_env.py
import os
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Optional, Dict, Any, Tuple


class NoctriaFXTradingEnv(gym.Env):
    """
    最小テンプレ（SB3推論・学習兼用）

    観測:
      - 連続 N 次元（既定は 6。既存のSB3モデル: Box(-inf, inf, (6,), float32) に合わせる）
      - 将来 8 列仕様で再学習する場合は obs_dim=8（または環境変数で上書き）
        環境変数: NOCTRIA_ENV_OBS_DIM または PROMETHEUS_OBS_DIM

    行動:
      - Discrete(3) = {0: SELL, 1: HOLD, 2: BUY}

    終了条件:
      - max_episode_steps 到達で truncated=True（terminated はこのテンプレでは常に False）

    備考:
      - 既存モデルで推論する時は obs_dim=6 のまま
      - 8列で新規学習→保存したモデルは Box(..., (8,), float32) 固定になる
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
        # 追加: 観測次元（未指定なら環境変数→既定6）
        obs_dim: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.window = int(window)
        self.fee = float(fee)
        self.reward_mode = str(reward_mode)
        self.max_episode_steps = int(max_episode_steps)
        self.render_mode = render_mode

        env_obs_dim = (
            obs_dim
            or _to_int_or_none(os.environ.get("NOCTRIA_ENV_OBS_DIM"))
            or _to_int_or_none(os.environ.get("PROMETHEUS_OBS_DIM"))
            or 6  # 既定は6（現行SB3モデル互換）
        )
        if env_obs_dim is None or env_obs_dim <= 0:
            raise ValueError(f"obs_dim must be positive int, got {env_obs_dim}")
        self.obs_dim = int(env_obs_dim)

        # 観測/行動空間の定義（SB3要件: dtype=float32）
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.obs_dim,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(3)  # 0:SELL / 1:HOLD / 2:BUY

        # 乱数生成器
        self._rng = np.random.default_rng(seed)
        self._state = np.zeros(self.obs_dim, dtype=np.float32)
        self._t = 0

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            # 独自のGeneratorもseedを反映
            self._rng = np.random.default_rng(seed)

        # 常に (obs_dim,) float32 を返す
        self._state = self._rng.normal(0, 0.1, size=(self.obs_dim,)).astype(np.float32)
        self._state = np.nan_to_num(self._state, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        self._t = 0
        info: Dict[str, Any] = {}
        return self._state.astype(np.float32, copy=False), info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        assert self.action_space.contains(action), f"invalid action {action}"

        # ダミー遷移（数値安定化）
        self._state = (self._state + self._rng.normal(0, 0.05, size=(self.obs_dim,))).astype(np.float32)
        self._state = np.nan_to_num(self._state, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

        # ダミー報酬（本番はPnL等へ差し替え）
        base = 0.1 if action == 2 else (0.0 if action == 1 else -0.05)
        reward = float(self._rng.normal(base, 0.1))
        if action in (0, 2):
            reward -= self.fee
        reward = float(np.nan_to_num(reward, nan=0.0, posinf=0.0, neginf=0.0))

        self._t += 1
        terminated = False
        truncated = self._t >= self.max_episode_steps
        info: Dict[str, Any] = {}

        # SB3互換: 観測は必ず float32 の (obs_dim,)
        return self._state.astype(np.float32, copy=False), reward, terminated, truncated, info

    def render(self) -> None:
        pass

    def close(self) -> None:
        pass


def _to_int_or_none(x: Optional[str]) -> Optional[int]:
    if x is None:
        return None
    try:
        return int(x.strip())
    except Exception:
        return None
