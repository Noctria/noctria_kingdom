from unittest.mock import MagicMock
from model_evaluation import evaluate_model

def test_evaluate_model():
    """Test model evaluation."""
    mock_model = MagicMock()
    mock_model.predict.return_value = [0.1]*100
    X_test, y_test = [[0.1]*10]*100, [0.1]*100
    mse, mae = evaluate_model(mock_model, X_test, y_test)
    assert mse >= 0
    assert mae >= 0
python
