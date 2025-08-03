import unittest
from unittest.mock import patch
from data_fetcher import DataFetcher

class TestDataFetcher(unittest.TestCase):
    # テストケース: 正常なデータ取得
    # 目的: データを正常に取得できるかを確認
    # 説明責任: APIが200ステータスを返すシナリオの確認
    @patch('data_fetcher.requests.get')
    def test_fetch_data_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'price': 150}

        fetcher = DataFetcher()
        data = fetcher.fetch_data()
        self.assertEqual(data, {'price': 150})

    # テストケース: 異常なデータ取得
    # 目的: サーバエラー等異常状態の対応を確認
    # 説明責任: APIが200以外のステータスを返すシナリオの確認
    @patch('data_fetcher.requests.get')
    def test_fetch_data_failure(self, mock_get):
        mock_get.return_value.status_code = 500

        fetcher = DataFetcher()
        with self.assertRaises(Exception):
            fetcher.fetch_data()

if __name__ == '__main__':
    unittest.main()
