from typing import Tuple
from keras.models import Sequential
from keras.layers import LSTM, Dense
import logging

def build_model(input_shape: Tuple[int, ...]) -> Sequential:
    """Build an LSTM based model."""
    try:
        model = Sequential()
        model.add(LSTM(50, input_shape=input_shape, return_sequences=True))
        model.add(LSTM(50, return_sequences=False))
        model.add(Dense(1))
        model.compile(optimizer='adam', loss='mse')
        return model
    except Exception as e:
        logging.error(f"Error building model: {e}")
        raise
