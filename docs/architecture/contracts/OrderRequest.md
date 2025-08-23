# ⚔️ Contract: OrderRequest v1.1

> Do層（execution）に送信する**発注リクエスト**。  
> v1.1 で **idempotency_key**（冪等性キー）を追加 — 後方互換（任意フィールド）。

- **Producers**: DecisionEngine / RiskGate（NoctusGate）
- **Consumers**: Execution API (`order_execution.py`)
- **Schema Version**: `1.1.0` (semver)
- **Content-Type**: `application/json; charset=utf-8`

---

## JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://noctria.ai/schemas/orderrequest-1.1.json",
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

    "idempotency_key": {
      "type": "string",
      "description": "HMAC-SHA256(secret, 'symbol|side|qty|ts_floor_minute|trace_id') を 64 hex で表現（任意だが推奨）",
      "minLength": 32,
      "maxLength": 128
    },

    "ts": { "type": "string", "format": "date-time" },
    "schema_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" }
  },
  "allOf": [
    { "if": { "properties": { "type": { "const": "LIMIT" } } }, "then": { "required": ["price"] } },
    { "if": { "properties": { "type": { "const": "STOP_LIMIT" } } }, "then": { "required": ["price"] } }
  ],
  "additionalProperties": false
}
