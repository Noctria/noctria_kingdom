# ファイル名: test_data_fetcher.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T17:48:45.912027
# 生成AI: openai_noctria_dev.py
# UUID: c8d832da-2301-49c2-9a08-d5c122471193
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

# 説明: データ取得モジュールのテスト
# バージョン: 1.0.0

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
```

### strategy_decider.pyのテストコード

```python