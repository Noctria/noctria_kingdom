# @ファイル名: path_config.py
# バージョン: v0.1.1
# 生成日時: 2025-08-03Txx:xx:xx.xxxxxx
# 生成AI: openai_noctria_dev.py

# データ取得関連
DATA_SOURCE_URL = "https://api.example.com/usd_jpy"
DATA_API_ENDPOINT = "https://api.example.com/market"

# モデル保存先
MODEL_SAVE_PATH = "./models/usd_jpy_model.h5"

# データ・特徴量保存ディレクトリ
LOCAL_DATA_PATH = "./local_data/"
FEATURES_PATH = "./features/"
DATA_PATH = "/dummy/data/path"  # テスト用ダミーパス

def get_path(name):
    # nameに応じたダミーパスを返す（テスト時はこれで十分）
    return f"./local_data/{name}"
