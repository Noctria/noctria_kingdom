from keras.models import Sequential
from sklearn.metrics import mean_squared_error, mean_absolute_error
import logging

def evaluate_model(model: Sequential, X_test, y_test):
    """Evaluate the trained model."""
    try:
        predictions = model.predict(X_test)
        mse = mean_squared_error(y_test, predictions)
        mae = mean_absolute_error(y_test, predictions)
        logging.info(f"Model Evaluation: MSE={mse}, MAE={mae}")
        return mse, mae
    except Exception as e:
        logging.error(f"Error evaluating model: {e}")
        raise
