
---

# 3) `OrderRequest.md`
```markdown
# ⚔️ Contract: OrderRequest v1.0

> Do層（execution）に送信する**発注リクエスト**。

- **Producers**: DecisionEngine / RiskGate
- **Consumers**: Execution API (`order_execution.py`)
- **Schema Version**: `1.0.0`

## JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://noctria.ai/schemas/orderrequest-1.0.json",
  "title": "OrderRequest",
  "type": "object",
  "required": ["trace_id","decision_id","symbol","side","type","quantity","ts","schema_version"],
  "properties": {
    "trace_id": { "type": "string" },
    "decision_id": { "type": "string" },
    "symbol": { "type": "string" },
    "side": { "type": "string", "enum": ["BUY","SELL"] },
    "type": { "type": "string", "enum": ["MARKET","LIMIT","STOP","STOP_LIMIT"] },
    "quantity": { "type": "number", "exclusiveMinimum": 0 },
    "price": { "type": "number" },
    "time_in_force": { "type": "string", "enum": ["GTC","IOC","FOK","DAY"], "default": "GTC" },
    "client_order_id": { "type": "string" },
    "ts": { "type": "string", "format": "date-time" },
    "schema_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" }
  },
  "allOf": [
    {
      "if": { "properties": { "type": { "const": "LIMIT" } } },
      "then": { "required": ["price"] }
    },
    {
      "if": { "properties": { "type": { "const": "STOP_LIMIT" } } },
      "then": { "required": ["price"] }
    }
  ],
  "additionalProperties": false
}
