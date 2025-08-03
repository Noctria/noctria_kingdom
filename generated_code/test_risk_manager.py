import unittest
from risk_manager import RiskManager

class TestRiskManager(unittest.TestCase):
    # テストケース: ポジションサイズ計算
    # 目的: ポジションサイズが正しく計算されるか確認
    # 説明責任: リスクレベルに応じた資金活用の妥当性
    def test_calculate_position_size(self):
        manager = RiskManager()
        position_size = manager.calculate_position_size(10000, 5)
        self.assertEqual(position_size, 500)

if __name__ == '__main__':
    unittest.main()
