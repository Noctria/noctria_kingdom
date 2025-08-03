import pandas as pd
from model_training import train_model
from path_config import FEATURES_PATH

def test_train_model():
    data = pd.DataFrame({
        'Feature1': [0, 1, 0, 1, 0, 1],
        'Feature2': [1, 0, 1, 0, 1, 0],
        'Target': [0, 1, 0, 1, 0, 1]
    })
    data.to_csv(FEATURES_PATH, index=False)

    # 訓練を実行して、エラーが発生しないことのみ確認
    train_model()  # 戻り値がなく、print出力を確認することができないが、例外がないことを確認
python
