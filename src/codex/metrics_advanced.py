# [NOCTRIA_CORE_REQUIRED]
from __future__ import annotations

from typing import Sequence

import numpy as np


# --- 新規性 ---
def novelty_rate(feature_vectors: Sequence[Sequence[float]]) -> float:
    """1 - 平均コサイン類似度（ベクトルが1本以下なら0.0）。"""
    if len(feature_vectors) <= 1:
        return 0.0
    X = np.array(feature_vectors, dtype=float)
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
    sims = []
    for i in range(len(X)):
        for j in range(i + 1, len(X)):
            sims.append(float(np.dot(X[i], X[j])))
    mean_sim = float(np.mean(sims)) if sims else 1.0
    return max(0.0, min(1.0, 1.0 - mean_sim))


def novelty_pass_rate(passed_flags: Sequence[bool]) -> float:
    """新規性ありと判定した提案のうち合格の比率。"""
    if not passed_flags:
        return 0.0
    return sum(1 for f in passed_flags if f) / len(passed_flags)


# --- 校正 ---
def brier_score(y_prob: Sequence[float], y_true: Sequence[int]) -> float:
    y_prob = np.clip(np.array(y_prob, float), 1e-6, 1 - 1e-6)
    y_true = np.array(y_true, int)
    return float(np.mean((y_prob - y_true) ** 2))


def ece_calibration(y_prob: Sequence[float], y_true: Sequence[int], bins: int = 10) -> float:
    y_prob = np.clip(np.array(y_prob, float), 1e-6, 1 - 1e-6)
    y_true = np.array(y_true, int)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for i in range(bins):
        mask = (y_prob >= edges[i]) & (y_prob < edges[i + 1])
        if not np.any(mask):
            continue
        conf = float(np.mean(y_prob[mask]))
        acc = float(np.mean(y_true[mask]))
        ece += (np.sum(mask) / len(y_prob)) * abs(acc - conf)
    return float(ece)


# --- ツール効率 ---
class ToolMeter:
    def __init__(self):
        self.calls = 0
        self.solved = 0
        self.latencies = []

    def record(self, solved: bool, latency_sec: float) -> None:
        self.calls += 1
        if solved:
            self.solved += 1
        self.latencies.append(float(latency_sec))

    @property
    def tool_efficiency(self) -> float:
        return self.solved / self.calls if self.calls else 0.0

    @property
    def avg_latency(self) -> float:
        return float(np.mean(self.latencies)) if self.latencies else 0.0


# --- 自己内省 ---
def self_fix_success_rate(success_flags: Sequence[bool]) -> float:
    if not success_flags:
        return 0.0
    return sum(1 for f in success_flags if f) / len(success_flags)


def time_to_self_fix_min(start_ts: float, end_ts: float) -> float:
    return max(0.0, (end_ts - start_ts) / 60.0)


# --- 計画一貫性（簡易） ---
def plan_consistency_score(links_present: dict) -> float:
    """
    links_present: {'north_star->milestones':bool, 'milestones->tasks':bool, 'tasks->specs':bool}
    3本のリンク有無を0..1で採点（必要なら加重へ）。
    """
    keys = ["north_star->milestones", "milestones->tasks", "tasks->specs"]
    got = sum(1 for k in keys if links_present.get(k))
    return got / len(keys)


# --- 協調創作 ---
def handoff_success_rate(passed_next_stage: Sequence[bool]) -> float:
    if not passed_next_stage:
        return 0.0
    return sum(map(bool, passed_next_stage)) / len(passed_next_stage)


# --- temperature scaling (binary) ---
try:
    from scipy.optimize import minimize
except Exception:
    minimize = None


def temperature_scale(logits, y_true) -> float:
    """
    単純な温度スケーリング。scipy 無ければ T=1.0 を返す（無効化）。
    logits: 1次元ロジット（浮動小数）
    y_true: 0/1 ラベル
    """
    if minimize is None:
        return 1.0
    logits = np.asarray(logits, dtype=float)
    y_true = np.asarray(y_true, dtype=int)

    def nll(t_arr):
        T = max(1e-3, float(t_arr[0]))
        p = 1.0 / (1.0 + np.exp(-logits / T))
        eps = 1e-12
        return -np.mean(y_true * np.log(p + eps) + (1 - y_true) * np.log(1 - p + eps))

    res = minimize(nll, x0=[1.0], bounds=[(1e-3, 100.0)])
    return float(res.x[0])
