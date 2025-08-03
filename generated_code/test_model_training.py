# ファイル名: test_model_training.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:15:29.996336
# 生成AI: openai_noctria_dev.py
# UUID: 9009976c-a65f-4363-a5c2-2945311fd8ea
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
# test_model_training.py

import pandas as pd
import os
from model_training import train_model
from src.core.path_config import FEATURES_PATH, MODEL_PATH

def test_train_model(tmp_path):
    features = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [4, 5, 6]})
    target = pd.Series([1, 2, 3])
    model_output_path = tmp_path / "model.joblib"
    
    train_model(features, target, str(model_output_path))
    
    assert model_output_path.exists()
```