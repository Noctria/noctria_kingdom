| code | HTTP | 説明 | 再試行 |
|---|---:|---|---|
| `TRADING_PAUSED` | 409 | 全局抑制中 | ❌ |
| `RISK_BOUNDARY_EXCEEDED` | 422 | Noctus 境界越え | ❌ |
| `BROKER_REJECTED` | 424 | ブローカー拒否 | ⭕（修正後） |
| `TIMEOUT_RETRYING` | 504 | ブローカー遅延 | ⭕（指数バックオフ） |
| `RATE_LIMITED` | 429 | レート超過 | ⭕（`Retry-After`） |
| `INVALID_REQUEST` | 400 | スキーマ違反/丸め不能 | ❌ |

---

