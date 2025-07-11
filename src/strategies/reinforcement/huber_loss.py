import torch
import torch.nn as nn

class HuberLoss(nn.Module):
    """
    Huber Loss の実装
    - MSE と MAE の特性を組み合わせ、外れ値の影響を抑制
    """

    def __init__(self, delta=1.0):
        """
        初期化
        :param delta: 外れ値とみなす閾値
        """
        super(HuberLoss, self).__init__()
        self.delta = delta

    def forward(self, predictions, targets):
        """
        Huber Loss の計算
        :param predictions: 予測された Q 値
        :param targets: 実際の TD ターゲット値
        :return: Huber Loss 値
        """
        error = predictions - targets
        is_small_error = torch.abs(error) <= self.delta

        # MSE (誤差が小さい場合) / MAE (誤差が大きい場合)
        loss = torch.where(is_small_error, 0.5 * error ** 2, self.delta * (torch.abs(error) - 0.5 * self.delta))

        return loss.mean()
