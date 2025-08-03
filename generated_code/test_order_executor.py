import unittest
from unittest.mock import patch
from order_executor import OrderExecutor

class TestOrderExecutor(unittest.TestCase):
    # テストケース: 正常な注文実行
    # 目的: 注文が正常にAPIへ送信されるか確認
    # 説明責任: APIが200ステータスを返すシナリオの確認
    @patch('order_executor.requests.post')
    def test_execute_order_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'status': 'success'}

        executor = OrderExecutor()
        result = executor.execute_order('BUY')
        self.assertEqual(result, {'status': 'success'})

    # テストケース: 異常な注文実行
    # 目的: サーバエラー等異常状態の対応を確認
    # 説明責任: APIが200以外のステータスを返すシナリオ
    @patch('order_executor.requests.post')
    def test_execute_order_failure(self, mock_post):
        mock_post.return_value.status_code = 500

        executor = OrderExecutor()
        with self.assertRaises(Exception):
            executor.execute_order('SELL')

if __name__ == '__main__':
    unittest.main()
python
