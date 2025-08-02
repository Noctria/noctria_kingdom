def execute_trades(buy_signals, sell_signals):
    print("Executing trades.")
    for index, row in buy_signals.iterrows():
        print(f"Buying at {row['Date']} - Price: {row['Close']}")

    for index, row in sell_signals.iterrows():
        print(f"Selling at {row['Date']} - Price: {row['Close']}")
```

これらの改善点は、よりリアルで安全性の高い自動売買システムを構築するための一歩となります。