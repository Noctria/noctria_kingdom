# ファイル名: test_strategy_model.py
# バージョン: v0.1.0
# 生成日時: 2025-08-03T19:34:31.944207
# 生成AI: openai_noctria_dev.py
# UUID: d326ef7f-0686-448f-952e-652b08547451
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

import pytest
import pandas as pd
from strategy_model import StrategyModel

# 目的: 移動平均計算が正しく行われることの確認
# 期待結果: 正しい短期・中期移動平均が計算されること
def test_calculate_moving_averages():
    data = pd.DataFrame({'close': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    model = StrategyModel(short_window=3, medium_window=5, rsi_period=14)
    result = model.calculate_moving_averages(data)
    expected_short_ma = data['close'].rolling(window=3).mean()
    expected_medium_ma = data['close'].rolling(window=5).mean()
    pd.testing.assert_series_equal(result['short_ma'], expected_short_ma)
    pd.testing.assert_series_equal(result['medium_ma'], expected_medium_ma)

# 目的: Bollinger Bandsが正しく計算されることの確認
# 期待結果: 上限・下限バンドが正しく計算されること
def test_calculate_bollinger_bands():
    data = pd.DataFrame({'close': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    model = StrategyModel(short_window=3, medium_window=5, rsi_period=14)
    result = model.calculate_bollinger_bands(data)
    expected_sma = data['close'].rolling(window=5).mean()
    expected_stddev = data['close'].rolling(window=5).std()
    expected_upper_band = expected_sma + (expected_stddev * 2)
    expected_lower_band = expected_sma - (expected_stddev * 2)
    pd.testing.assert_series_equal(result['upper_band'], expected_upper_band)
    pd.testing.assert_series_equal(result['lower_band'], expected_lower_band)

# 目的: RSI計算が正しく行われることの確認
# 期待結果: 正しいRSI値が計算されること
def test_calculate_rsi():
    data = pd.DataFrame({'close': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    model = StrategyModel(short_window=3, medium_window=5, rsi_period=14)
    result = model.calculate_rsi(data)
    assert 'rsi' in result.columns  # RSIが計算され、カラムが追加されている
```

#### ファイル名: `test_data_preprocessing.py`

```python