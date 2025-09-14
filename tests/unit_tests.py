# tests/unit_tests.py
import unittest

# --- SUT imports --------------------------------------------------------------
from strategies.Aurus_Singularis import AurusSingularis
from execution.order_execution import OrderExecution

# `ORDER_TYPE_BUY` がプロジェクト側に定義されていればそれを使用し、
# 見つからない環境でもテストが動くようフォールバックを用意する
ORDER_TYPE_BUY = "BUY"
for _cand in (
    "execution.constants",
    "src.constants",
    "core.constants",
):
    try:
        ORDER_TYPE_BUY = __import__(_cand, fromlist=["ORDER_TYPE_BUY"]).ORDER_TYPE_BUY  # type: ignore[attr-defined]
        break
    except Exception:
        pass


class TestStrategy(unittest.TestCase):
    """戦略モジュールのユニットテスト"""

    def setUp(self):
        self.strategy = AurusSingularis()

    def test_model_initialization(self):
        """モデルが正しく初期化されるか確認"""
        self.assertIsNotNone(getattr(self.strategy, "model", None))


class TestOrderExecution(unittest.TestCase):
    """注文執行モジュールのユニットテスト"""

    def setUp(self):
        self.executor = OrderExecution()

    def test_execute_trade(self):
        """注文が正常に送信されるか確認"""
        result = self.executor.execute_trade(ORDER_TYPE_BUY, 0.1)
        self.assertIn("Trade", str(result))


if __name__ == "__main__":
    unittest.main()
