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
