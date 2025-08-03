import requests

from path_config import DATA_API_ENDPOINT

class DataFetcher:
    def __init__(self):
        self.api_endpoint = DATA_API_ENDPOINT

    def fetch_data(self):
        response = requests.get(self.api_endpoint)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception("データ取得失敗")

def log_difference_and_reason(old_data, new_data, reason):
    pass
