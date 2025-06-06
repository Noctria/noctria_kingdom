# data/lstm_data_processor.py

import numpy as np

class LSTMDataProcessor:
    """
    取得した市場データを、LSTM学習・予測用のシーケンスに変換するクラス。
    """

    def __init__(self, window_size=30):
        """
        :param window_size: LSTMが見る時間ステップの数
        """
        self.window_size = window_size

    def create_sequences(self, data):
        """
        LSTMの学習用に、スライディングウィンドウでシーケンスデータを作成。
        :param data: np.ndarray (行数, 特徴数)
        :return: (X, y) タプル。X.shape=(サンプル数, window_size, 特徴数), y.shape=(サンプル数,)
        """
        X, y = [], []
        for i in range(len(data) - self.windo
