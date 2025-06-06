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
        for i in range(len(data) - self.window_size):
            X.append(data[i:i + self.window_size])
            y.append(data[i + self.window_size][0])  # 予測対象は最初の特徴量と仮定
        return np.array(X), np.array(y)

    def prepare_single_sequence(self, data):
        """
        最新のデータから、1つだけ予測用のシーケンスを作成。
        :param data: np.ndarray (行数, 特徴数)
        :return: (1, window_size, 特徴数) のシーケンス
        """
        if len(data) < self.window_size:
            raise ValueError("データ長がwindow_size未満です")
        sequence = data[-self.window_size:]
        return sequence.reshape(1, self.window_size, -1)
