# ファイル名: test_order_execution.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T02:58:22.512816
# 生成AI: openai_noctria_dev.py
# UUID: 7301aa21-89ee-4466-84a4-24a6d927daa1
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

```python
import pytest
from generated_code.order_execution import execute_trade
from src.core.path_config import MODEL_PATH, FEATURES_PATH

def test_execute_trade(capfd):
    execute_trade(MODEL_PATH, FEATURES_PATH)
    captured = capfd.readouterr()
    expected_output = f"Executing trade with model: {MODEL_PATH} and features: {FEATURES_PATH}\n"
    assert captured.out == expected_output
```