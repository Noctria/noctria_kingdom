import unittest
from strategies.Aurus_Singularis import AurusSingularis
from execution.order_execution import OrderExecution

class TestStrategy(unittest.TestCase):
    """戦略モジュールのユニットテスト"""

    def setUp(self):
        self.strategy = AurusSingularis()

    def test_model_initialization(self):
        """モデルが正しく初期化されるか確認"""
        self.assertIsNotNone(self.strategy.model)

class TestOrderExecution(unittest.TestCase):
    """注文執行モジュールのユニットテスト"""

    def setUp(self):
        self.executor = OrderExecution()

    def test_execute_trade(self):
        """注文が正常に送信されるか確認"""
        result = self.executor.execute_trade(ORDER_TYPE_BUY, 0.1)
        self.assertIn("Trade", result)

if __name__ == "__main__":
    unittest.main()
