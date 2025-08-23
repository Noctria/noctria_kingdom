
---

# 4) `DecisionRecord.md`
```markdown
# 👑 Contract: DecisionRecord v1.0

> DecisionEngine が **StrategyProposal** を評価し、最終判断・根拠・ロットを確定した**裁定記録**。

- **Producer**: DecisionEngine（＋ NoctusGate / QualityGate / Profiles）
- **Consumers**: GUI / Analytics / Auditing
- **Schema Version**: `1.0.0`

## JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://noctria.ai/schemas/decisionrecord-1.0.json",
  "title": "DecisionRecord",
  "type": "object",
  "required": ["decision_id","trace_id","as_of","final_action","lot","sources","reasons","schema_version"],
  "properties": {
    "decision_id": { "type": "string" },
    "trace_id": { "type": "string" },
    "as_of": { "type": "string", "format": "date-time" },
    "final_action": { "type": "string", "enum": ["BUY","SELL","FLAT","HOLD"] },
    "symbol": { "type": "string" },
    "lot": { "type": "number", "minimum": 0 },
    "risk": {
      "type": "object",
      "properties": {
        "max_drawdown_pct": { "type": "number" },
        "expected_slippage": { "type": "number" },
        "profile": { "type": "string" }
      },
      "additionalProperties": true
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["agent","action","confidence"],
        "properties": {
          "agent": { "type": "string" },
          "action": { "type": "string" },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
        },
        "additionalProperties": true
      }
    },
    "reasons": { "type": "array", "items": { "type": "string" } },
    "constraints_applied": {
      "type": "array",
      "items": { "type": "string" }
    },
    "schema_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" }
  },
  "additionalProperties": false
}
