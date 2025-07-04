import numpy as np
import cvxpy as cp

class PortfolioOptimizer:
    """
    ポートフォリオ最適化戦略
    - リスク最小化とリターン最大化のバランスを調整
    - 最適な資産配分を算出
    """

    def __init__(self, num_assets, risk_tolerance=0.05):
        """
        初期化
        :param num_assets: 資産の種類
        :param risk_tolerance: 許容リスクの閾値
        """
        self.num_assets = num_assets
        self.risk_tolerance = risk_tolerance

    def optimize(self, expected_returns, covariance_matrix):
        """
        ポートフォリオ最適化の実行
        :param expected_returns: 各資産の期待リターン (NumPy 配列)
        :param covariance_matrix: 各資産の共分散行列 (NumPy 配列)
        :return: 最適化された資産配分 (NumPy 配列)
        """
        weights = cp.Variable(self.num_assets)

        # 目的関数: リスク最小化とリターン最大化のバランス
        expected_return = expected_returns @ weights
        risk = cp.quad_form(weights, covariance_matrix)

        # 制約条件
        constraints = [
            cp.sum(weights) == 1,   # 全資産の合計は 1
            weights >= 0,           # ネガティブウェイトなし (ショート禁止)
            risk <= self.risk_tolerance  # 許容リスク以下
        ]

        # 最適化問題を解く
        problem = cp.Problem(cp.Maximize(expected_return - risk), constraints)
        problem.solve()

        return weights.value
