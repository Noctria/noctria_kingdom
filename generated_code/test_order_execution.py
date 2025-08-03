import pandas as pd
from unittest.mock import patch
from order_execution import execute_trade
from path_config import MODEL_PATH, FEATURES_PATH

@patch('order_execution.pickle.load')
def test_execute_trade(mock_model_load):
    # モックモデルが予測を返すように設定
    class MockModel:
        def predict(self, X):
            return [1, 0, 1]

    mock_model_load.return_value = MockModel()

    data = pd.DataFrame({'Feature1': [0, 1, 0], 'Feature2': [1, 0, 1]})
    data.to_csv(FEATURES_PATH, index=False)

    execute_trade()  # print出力を視覚的に確認する
