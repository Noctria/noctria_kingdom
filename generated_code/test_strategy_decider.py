import unittest
from strategy_decider import StrategyDecider

class TestStrategyDecider(unittest.TestCase):
    # テストケース: 買いシグナルの決定
    # 目的: 買いシグナル生成の正当性を確認
    # 説明責任: 短期MAが長期MAを超えるシナリオ
    def test_decide_signal_buy(self):
        decider = StrategyDecider()
        market_data = [100, 105, 110, 115, 120]
        signal = decider.decide_signal(market_data)
        self.assertEqual(signal, 'BUY')

    # テストケース: 売りシグナルの決定
    # 目的: 売りシグナル生成の正当性を確認
    # 説明責任: 短期MAが長期MAを下回るシナリオ
    def test_decide_signal_sell(self):
        decider = StrategyDecider()
        market_data = [120, 115, 110, 105, 100]
        signal = decider.decide_signal(market_data)
        self.assertEqual(signal, 'SELL')

    # テストケース: ホールドシグナルの決定
    # 目的: ホールドシグナル生成の正当性を確認
    # 説明責任: 短期MAと長期MAが等しいシナリオ
    def test_decide_signal_hold(self):
        decider = StrategyDecider()
        market_data = [110, 111, 112, 112, 114]
        signal = decider.decide_signal(market_data)
        self.assertEqual(signal, 'HOLD')

if __name__ == '__main__':
    unittest.main()
python
