# Fintokei ルール査定レポート
- Trace ID: `pdca_20250920_044036`
- Evaluated: 2025-09-20T04:44:23+09:00
- Result: VETO ❌ (ERRORあり)

## Plan
```json
{
  "symbol": "USDJPY",
  "side": "buy",
  "entry_price": 157.2,
  "stop_loss_price": 156.7,
  "lot": 0.8,
  "capital": 200000.0,
  "target_profit_total": 20000.0
}
```

## Violations
- **ERROR** `MAX_RISK_EXCEEDED`: 1取引リスク 20.00% が上限 5.0% を超過
  ```json
{
  "risk_pct": 20.0,
  "risk_amt": 40000.0,
  "capital": 200000.0
}
  ```
