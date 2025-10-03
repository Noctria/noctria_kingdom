# [NOCTRIA_CORE_REQUIRED] minimal adversarial suite
from __future__ import annotations

from typing import List

import numpy as np


def _noise_injection(p: np.ndarray, level: float = 0.05) -> np.ndarray:
    noise = np.random.normal(0.0, level, size=p.shape)
    return np.clip(p + noise, 0.0, 1.0)


def _time_shift(p: np.ndarray, k: int = 1) -> np.ndarray:
    if k <= 0:
        return p
    q = np.roll(p, k)
    q[:k] = float(np.median(p))
    return q


def _regime_flip(p: np.ndarray, strength: float = 0.2) -> np.ndarray:
    n = p.shape[0]
    drift = np.linspace(-strength, strength, num=n)
    return np.clip(p + drift, 0.0, 1.0)


def _binary_acc(p: np.ndarray, y: np.ndarray, thr: float = 0.5) -> float:
    return float(np.mean((p >= thr).astype(int) == y))


def run_adversarial_suite(
    reports_dir,
    base_probs: List[float],
    y_true: List[int],
    min_cases_per_type: int = 10,
    thr: float = 0.5,
) -> List[bool]:
    p0 = np.asarray(base_probs, dtype=float)
    y = np.asarray(y_true, dtype=int)
    base_acc = _binary_acc(p0, y, thr=thr)
    target = 0.9 * base_acc  # 通常の 90% を維持できれば pass

    passes: List[bool] = []
    for i in range(min_cases_per_type):
        pi = _noise_injection(p0, level=0.05 + 0.01 * i)
        passes.append(_binary_acc(pi, y, thr=thr) >= target)
    for k in range(1, min_cases_per_type + 1):
        pi = _time_shift(p0, k=k)
        passes.append(_binary_acc(pi, y, thr=thr) >= target)
    for i in range(min_cases_per_type):
        pi = _regime_flip(p0, strength=0.1 + 0.02 * i)
        passes.append(_binary_acc(pi, y, thr=thr) >= target)
    return passes
