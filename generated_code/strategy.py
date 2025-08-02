def calculate_sma(data, window):
    return data['Close'].rolling(window=window).mean()

def generate_signals(data, short_window=5, long_window=20):
    print("Generating signals.")
    data['SMA_Short'] = calculate_sma(data, short_window)
    data['SMA_Long'] = calculate_sma(data, long_window)

    buy_signals = data[(data['SMA_Short'] > data['SMA_Long']) &
                       (data['SMA_Short'].shift(1) <= data['SMA_Long'].shift(1))]
    sell_signals = data[(data['SMA_Short'] < data['SMA_Long']) &
                        (data['SMA_Short'].shift(1) >= data['SMA_Long'].shift(1))]

    return buy_signals, sell_signals
```

#### order_execution.py

```python