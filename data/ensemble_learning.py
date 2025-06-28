import numpy as np

class EnsembleLearning:
    """複数モデルを統合し、最適な市場予測を行う"""
    
    def __init__(self, models):
        self.models = models
    
    def predict(self, market_data):
        """各モデルの予測を統合"""
        predictions = [model.predict(market_data) for model in self.models]
        return np.mean(predictions)

# ✅ アンサンブル学習適用テスト
if __name__ == "__main__":
    mock_models = [lambda x: x["price"] * 1.01, lambda x: x["price"] * 0.99]
    ensemble = EnsembleLearning(mock_models)
    market_data = {"price": 1.2500}
    prediction = ensemble.predict(market_data)
    print("Ensemble Prediction:", prediction)
