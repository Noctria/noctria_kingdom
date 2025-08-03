DATA_SOURCE_URL = "https://api.example.com/usd_jpy"
DATA_API_ENDPOINT = "https://api.example.com/market"

MODEL_SAVE_PATH = "./models/usd_jpy_model.h5"

LOCAL_DATA_PATH = "./local_data/"
FEATURES_PATH = "./features/"
DATA_PATH = "/dummy/data/path"  # テスト用ダミーパス

def get_path(name):
    # nameに応じたダミーパスを返す（テスト時はこれで十分）
    return f"./local_data/{name}"
