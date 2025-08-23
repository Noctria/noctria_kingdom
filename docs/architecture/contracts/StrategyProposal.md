
---

# 2) `StrategyProposal.md`
```markdown
# 🧠 Contract: StrategyProposal v1.0

> AI（Aurus/Levia/Prometheus/Veritas/Hermes など）が出力する**戦略提案**。

- **Producers**: AI strategies
- **Consumers**: DecisionEngine / GUI
- **Schema Version**: `1.0.0`

## JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://noctria.ai/schemas/strategyproposal-1.0.json",
  "title": "StrategyProposal",
  "type": "object",
  "required": ["trace_id","as_of","agent","decision","confidence","rationale","schema_version"],
  "properties": {
    "trace_id": { "type": "string", "minLength": 1 },
    "as_of": { "type": "string", "format": "date-time" },
    "agent": {
      "type": "object",
      "required": ["name","version"],
      "properties": {
        "name": { "type": "string", "examples": ["Aurus","Levia","Prometheus","Veritas","Hermes"] },
        "version": { "type": "string" }
      },
      "additionalProperties": false
    },
    "decision": {
      "type": "object",
      "required": ["action"],
      "properties": {
        "action": { "type": "string", "enum": ["BUY","SELL","FLAT","HOLD","SCALP"] },
        "symbol": { "type": "string" },
        "target_price": { "type": "number" },
        "stop_price": { "type": "number" },
        "time_horizon": { "type": "string", "examples": ["PT5M","PT1H","P1D"] }
      },
      "additionalProperties": true
    },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "rationale": { "type": "string", "minLength": 1 },
    "constraints": {
      "type": "object",
      "properties": {
        "max_order_qty": { "type": "number", "minimum": 0 },
        "risk_level": { "type": "string", "enum": ["LOW","MID","HIGH"] }
      },
      "additionalProperties": true
    },
    "schema_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" }
  },
  "additionalProperties": false
}
