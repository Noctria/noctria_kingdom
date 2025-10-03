# 例: utils/calibration.py に
import numpy as np
from scipy.optimize import minimize


def temperature_scale(logits, y_true):
    # 負の対数尤度を最小化
    def nll(T):
        p = 1 / (1 + np.exp(-logits / np.clip(T[0], 1e-3, 100)))
        eps = 1e-12
        return -np.mean(y_true * np.log(p + eps) + (1 - y_true) * np.log(1 - p + eps))

    res = minimize(nll, x0=[1.0], bounds=[(1e-3, 100)])
    return float(res.x[0])
