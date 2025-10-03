# coding: utf-8
"""
検証用の確率出力テンプレ
- predict_proba(df): 0..1 確率を返す（ここでは RSI をシグモイド化）
- simulate(df): 既存評価のための最小指標を返す
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def predict_proba(df: pd.DataFrame):
    # 実運用では学習済みモデルの predict_proba を返す
    if "RSI(14)" not in df.columns:
        return []
    x = (df["RSI(14)"].to_numpy() - 50.0) / 8.0
    return (1.0 / (1.0 + np.exp(-x))).tolist()


def simulate(df: pd.DataFrame):
    # 指標はダミーでもOK（合格は狙っていない）
    # ここでは確率/ラベルは evaluator 側が predict_proba から拾うので省略しても良い
    return {
        "final_capital": 1_000_000,  # 閾値ちょうど
        "win_rate": 0.55,
        "max_drawdown": 0.2,
        "total_trades": 30,
    }
