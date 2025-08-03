import pandas as pd
from ml_model import VeritasModel
from path_config import get_path
from src.core.king_noctria import execute_order

class TradingStrategy:
    def __init__(self) -> None:
        self.model = VeritasModel()

    def load_data(self) -> None:
        data_path = get_path('trading')
        self.data = pd.read_csv(f"{data_path}/market_data.csv")

    def generate_signals(self) -> None:
        # 予測に基づく売買シグナルを生成する
        predictions = self.model.predict(self.data.iloc[:, 1:11])  # Assuming the first 10 columns are features
        self.data['signals'] = ['buy' if x > 0 else 'sell' for x in predictions.flatten()]

    def execute_trades(self) -> None:
        for _, row in self.data.iterrows():
            execute_order(row['signals'], row['close'])

strategy = TradingStrategy()
strategy.load_data()
strategy.generate_signals()
strategy.execute_trades()
