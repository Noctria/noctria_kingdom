import pandas as pd

class RawDataLoader:
    """市場データを取得し、前処理を行うモジュール"""
    
    def __init__(self, source="market_data.csv"):
        self.source = source
    
    def load_data(self):
        """市場データを取得"""
        data = pd.read_csv(self.source)
        return data

    def preprocess(self, data):
        """欠損値処理と異常値除去"""
        data.dropna(inplace=True)
        data = data[(data["price"] > 0) & (data["volume"] > 0)]
        return data

# ✅ データ取得テスト
if __name__ == "__main__":
    loader = RawDataLoader()
    raw_data = loader.load_data()
    clean_data = loader.preprocess(raw_data)
    print("Preprocessed Data Sample:", clean_data.head())
