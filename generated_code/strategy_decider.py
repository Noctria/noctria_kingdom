import numpy as np
from path_config import STRATEGY_PARAMS

class StrategyDecider:
    def __init__(self):
        self.params = STRATEGY_PARAMS

    def decide_signal(self, market_data):
        # 移動平均クロスオーバーの実装例
        short_ma = np.mean(market_data[-self.params['short_window']:])
        long_ma = np.mean(market_data[-self.params['long_window']:])
        if short_ma > long_ma:
            return 'BUY'
        elif short_ma < long_ma:
            return 'SELL'
        else:
            return 'HOLD'

def log_difference_and_reason(old_data, new_data, reason):
    # 実装に応じた差分記録
    pass
