import requests
from unittest.mock import patch
from data_collection import fetch_forex_data
from path_config import DATA_SOURCE_URL, LOCAL_DATA_PATH

@patch('data_collection.requests.get')
def test_fetch_forex_data_success(mock_get):
    class MockResponse:
        status_code = 200
        text = "Sample data"

    mock_get.return_value = MockResponse()

    fetch_forex_data()  # 戻り値がないためエラーがないことを確認

    with open(LOCAL_DATA_PATH, 'r') as file:
        data = file.read()
        assert data == "Sample data"

@patch('data_collection.requests.get')
def test_fetch_forex_data_failure(mock_get):
    class MockResponse:
        status_code = 404
    
    mock_get.return_value = MockResponse()

    with pytest.raises(ConnectionError):
        fetch_forex_data()
