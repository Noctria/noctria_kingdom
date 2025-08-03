# test_turn1.py

import pytest
from unittest.mock import patch

# --- fetch_forex_dataのimportまたはダミー定義（本番は適切にimport） ---
# from data_pipeline import fetch_forex_data
def fetch_forex_data():
    pass

def test_fetch_forex_data_success():
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'rate': '110.00'}
        fetch_forex_data()
        mock_get.assert_called_once_with("https://api.forexdata.com/usd_jpy")

def test_fetch_forex_data_failure():
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 500
        fetch_forex_data()
        # 本来はエラーハンドリングのassertを入れる

# --- 他セクションのテストも同様にimport/ダミー定義を追加して実装 ---
