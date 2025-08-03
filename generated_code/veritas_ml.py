import pandas as pd
from keras.models import Sequential
import tensorflow as tf
from path_config import PathConfig

class VeritasML:
    def __init__(self, path_config: PathConfig):
        self.model_dir = path_config.MODEL_DIR

    def train_model(self, training_data: tf.data.Dataset) -> None:
        try:
            model = tf.keras.models.Sequential([  # 仮のモデル層
                tf.keras.layers.Dense(10, activation='relu'),
                tf.keras.layers.Dense(1)
            ])
            model.compile(optimizer='adam', loss='mean_squared_error')
            model.fit(training_data, epochs=10)
            model.save(f"{self.model_dir}/model.h5")
        except Exception as e:
            print(f"モデルトレーニング中にエラーが発生: {e}")

    def predict(self, data: pd.DataFrame) -> list:
        try:
            loaded_model = tf.keras.models.load_model(f"{self.model_dir}/model.h5")
            predictions = loaded_model.predict(data)
            return predictions.tolist()
        except Exception as e:
            print(f"予測中にエラーが発生: {e}")
            return []
