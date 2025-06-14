def calculate_reward(profit, drawdown, win_rate, recent_profits):
    """
    Noctria Kingdom版報酬関数
    利益最大化 + ドローダウン抑制 + 勝率ボーナス + 安定性ボーナス
    """
    reward = profit

    max_drawdown_threshold = -30
    if drawdown < max_drawdown_threshold:
        reward += drawdown  # 大きなDDはマイナス評価

    if win_rate > 0.6:
        reward += 10  # 勝率が高ければ加点

    if len(recent_profits) > 1:
        import numpy as np
        std_dev = np.std(recent_profits)
        stability_bonus = 5 / (1 + std_dev)
        reward += stability_bonus
    else:
        stability_bonus = 0

    return reward
