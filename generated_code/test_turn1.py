# ファイル名: test_turn1.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T10:55:54.303052
# 生成AI: openai_noctria_dev.py
# UUID: 8eef4de7-b3aa-4a3c-9508-fcfeefa02720

このコードスケルトンに対して、各モジュールの機能をテストするための`pytest`/`unittest`用テストコードを作成します。テストコードでは、正常系、異常系、そしてモジュール間の統合連携テストを含めます。また、パス設定などは`path_config.py`からインポートします。

以下はその実装例です。

### `tests/test_data_feed.py`

```python
import pytest
import pandas as pd
from data_feed import fetch_usd_jpy_data, preprocess_data
from unittest.mock import patch
import requests

@patch('data_feed.requests.get')
def test_fetch_usd_jpy_data(mock_get):
    # Mock response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{'timestamp': '2023-01-01T00:00:00Z', 'rate': 130.0}]
    
    df = fetch_usd_jpy_data()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty

@patch('data_feed.requests.get')
def test_fetch_usd_jpy_data_error(mock_get):
    # Simulate an error response
    mock_get.side_effect = requests.exceptions.RequestException("API Error")
    
    with pytest.raises(requests.exceptions.RequestException):
        fetch_usd_jpy_data()

def test_preprocess_data():
    # Sample data
    data = [{'timestamp': '2023-01-01T00:00:00Z', 'rate': 130.0}]
    df = pd.DataFrame(data)
    processed_df = preprocess_data(df)
    
    assert processed_df.index.name == 'timestamp'
    assert 'rate' in processed_df.columns
```

### `tests/test_model_training.py`

```python
import pytest
from model_training import train_model
import pandas as pd
from unittest.mock import patch

@patch('veritas.Model.save')
@patch('veritas.Model.train')
@patch('veritas.Model')
def test_train_model(mock_model_class, mock_train, mock_save):
    # Initialize mock
    mock_model_instance = mock_model_class.return_value
    
    # Sample data
    data = pd.DataFrame({'feature': [1, 2, 3], 'label': [0, 1, 0]})
    
    train_model(data)
    
    mock_train.assert_called_once_with(data)
    mock_save.assert_called_once_with("model_output_path")
```

### `tests/test_trading_strategy.py`

```python
import pandas as pd
from trading_strategy import generate_signals

def test_generate_signals():
    # Sample model output
    model_output = pd.DataFrame({'prediction': [0.1, -0.1, 0.0]})
    
    signals = generate_signals(model_output)
    
    assert 'signal' in signals.columns
    assert list(signals['signal']) == ['buy', 'sell', 'sell']
```

### `tests/test_order_execution.py`

```python
from order_execution import execute_order
from unittest.mock import patch

@patch('order_execution.print')
def test_execute_order_buy(mock_print):
    execute_order('buy')
    assert mock_print.called

@patch('order_execution.print')
def test_execute_order_sell(mock_print):
    execute_order('sell')
    assert mock_print.called

@patch('order_execution.print')
def test_execute_order_invalid(mock_print):
    execute_order('hold')
    mock_print.assert_called_with("No valid signal to execute: hold")
```

### 統合テスト

各モジュールが連携する統合テストは特に`scheduler.py`をベースにするのが自然ですが、Airflow DAGは通常、エンドツーエンドテストとしてではなく、各タスクのモック/シミュレーションによって検証されます。ここでは単体の整合性確認として以下のテストを追加します。

### `tests/test_scheduler.py`

```python
from scheduler import create_dag

def test_dag_integrity():
    dag = create_dag()
    # Check DAG ID
    assert dag.dag_id == 'usd_jpy_trading'
    # Check tasks count
    assert len(dag.tasks) == 4
```

これらのテストは、あなたの環境で`pytest`を使って実行することができます。テストケースにおいて、API呼び出しや学習モデルなどの外部依存がある場合はモックを使ってテストを実行可能にしています。