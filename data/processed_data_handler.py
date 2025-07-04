import pandas as pd
import numpy as np

class ProcessedDataHandler:
    """市場データの統合・特徴量抽出を行うモジュール"""
    
    def __init__(self):
        pass
    
    def normalize_data(self, data):
        """データを正規化"""
        return (data - data.min()) / (data.max() - data.min())

    def extract_features(self, data):
        """市場データから特徴量を抽出"""
        features = {
            "moving_avg": data["price"].rolling(window=5).mean(),
            "volatility": np.std(data["price"]),
            "momentum": data["price"].diff(),
        }
        return pd.DataFrame(features)

# ✅ データ処理テスト
if __name__ == "__main__":
    mock_data = pd.DataFrame({"price": np.random.uniform(1.2, 1.5, 100)})
    handler = ProcessedDataHandler()
    
    normalized_data = handler.normalize_data(mock_data["price"])
    extracted_features = handler.extract_features(mock_data)

    print("Normalized Data Sample:", normalized_data.head())
    print("Extracted Features:", extracted_features.head())
