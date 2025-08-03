import numpy as np
from ml_model import VeritasModel

def test_model_initialization():
    model = VeritasModel()
    assert model.model is not None

def test_model_predict():
    model = VeritasModel()
    features = np.random.rand(10, 10)  # Assuming input shape is (10,)
    predictions = model.predict(features)

    assert len(predictions) == 10
    assert isinstance(predictions, np.ndarray)
python
