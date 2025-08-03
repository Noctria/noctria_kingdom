import pandas as pd
from keras.models import Sequential
import tensorflow as tf
from path_config import get_path

class VeritasModel:
    def __init__(self) -> None:
        self.model = self._build_model()

    def _build_model(self) -> tf.keras.Model:
        model = tf.keras.models.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(10,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def train(self, data: dict) -> None:
        # Assuming 'features' and 'target' are keys in data
        self.model.fit(data['features'], data['target'], epochs=10)

    def predict(self, features: pd.DataFrame) -> pd.Series:
        return self.model.predict(features)
