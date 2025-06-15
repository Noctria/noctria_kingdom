def calculate_reward(profit, drawdown, win_rate, recent_profits):
    """
    🏰 Noctria Kingdom戦略報酬関数（Ver. 2）
    - 利益最大化（主目標）
    - ドローダウン抑制（耐久評価）
    - 勝率ボーナス（精度評価）
    - 安定性ボーナス（波の少ない支配を是とする）
    - 逆境耐性評価（赤字後の回復）
    """
    reward = profit

    # 📉 ドローダウン（強く抑制）
    if drawdown < -30:
        reward += drawdown * 1.5  # 厳しめに評価
    else:
        reward += drawdown * 0.5  # やや緩和

    # 🏆 勝率ボーナス
    if win_rate >= 0.7:
        reward += 15
    elif win_rate >= 0.6:
        reward += 10
    elif win_rate >= 0.5:
        reward += 5

    # 📊 安定性ボーナス
    if len(recent_profits) > 1:
        import numpy as np
        std_dev = np.std(recent_profits)
        stability_bonus = max(0, 5 / (1 + std_dev))
        reward += stability_bonus

    # 🔁 逆境耐性（赤字からの回復）
    if len(recent_profits) >= 2 and recent_profits[-2] < 0 < recent_profits[-1]:
        reward += 3  # 反発を正評価

    return round(reward, 4)
