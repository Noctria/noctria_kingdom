# 📦 Contract: FeatureBundle v1.0

> Plan層が生成し、AI/Decision が入力として利用する**標準特徴量バンドル**。

- **Producer**: PlanDataCollector / FeatureEngineer
- **Consumers**: Aurus / Levia / Prometheus / Veritas / Hermes / DecisionEngine
- **Schema Version**: `1.0.0` (semver)
- **Content-Type**: `application/json; charset=utf-8`

## JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://noctria.ai/schemas/featurebundle-1.0.json",
  "title": "FeatureBundle",
  "type": "object",
  "required": ["trace_id", "as_of", "features", "meta", "schema_version"],
  "properties": {
    "trace_id": { "type": "string", "minLength": 1 },
    "as_of": { "type": "string", "format": "date-time" },
    "features": {
      "type": "object",
      "additionalProperties": {
        "oneOf": [
          { "type": "number" },
          { "type": "string" },
          { "type": "boolean" }
        ]
      }
    },
    "meta": {
      "type": "object",
      "required": ["symbol", "interval", "tz"],
      "properties": {
        "symbol": { "type": "string", "minLength": 1 },
        "interval": { "type": "string", "examples": ["PT5M","PT1H","P1D"] },
        "tz": { "type": "string", "const": "UTC" }
      },
      "additionalProperties": true
    },
    "schema_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" }
  },
  "additionalProperties": false
}
