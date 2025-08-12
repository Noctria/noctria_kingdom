# 🔌 Noctria Kingdom API — Specification

**Version:** 1.1  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の PDCA（Plan/Do/Check/Act）および運用を支える **統一API** の仕様を定義する。  
> 参照：`../governance/Vision-Governance.md` / `../operations/Runbooks.md` / `../operations/Config-Registry.md` / `../operations/Airflow-DAGs.md` / `../security/Security-And-Access.md` / `./Do-Layer-Contract.md` / `../schemas/*.schema.json`

---

## 0. 概要（Overview）
- **Base URL**：`/api/v1`（内部/外部で同一パス。外部公開はゲート越し）
- **設計原則**：安全（ガードレール遵守）／監査可能（全操作に証跡）／少数で一貫したモデル  
- **領域**：`/plan`, `/do`, `/check`, `/act`, `/strategies`, `/config`, `/alerts`, `/ops`
- **配布物**：OpenAPI ドキュメント `GET /api/v1/openapi.json`（FastAPI 自動生成を正）

---

## 1. 認証・認可（AuthN/Z）
- **Auth**：`Authorization: Bearer <JWT>`（OIDC） or `Authorization: Noctria-Token <key>`（内部）
- **Scopes（例）**：`read:pdca`, `write:pdca`, `read:orders`, `write:orders`, `read:config`, `write:config`, `admin:ops`
- **ロール（参考）**：`ops`, `risk`, `models`, `readonly`（詳細は `../security/Security-And-Access.md`）
- **2FA**：GUI 経由の変更操作は 2FA 必須（`Config-Registry.md` の `gui.auth.require_2fa`）

---

## 2. 共通仕様（Conventions）
### 2.1 共通ヘッダ
- `Idempotency-Key`：**書き込み系で必須**。重複防止の保持期間は **24h**（Do-Layer §8 と統一）
- `X-Correlation-ID`：トレースID（未指定時はサーバが採番）
- `Content-Type: application/json; charset=utf-8`
- `RateLimit-Limit` / `RateLimit-Remaining` / `RateLimit-Reset`（秒）  
- `Deprecation` / `Link: <..>; rel="sunset"; param="YYYY-MM-DD"`（非推奨時）
- `ETag` / `If-Match`：**可変リソースの PATCH/PUT は If-Match 必須**（競合更新を防止）

### 2.2 エラー形式（統一）
```json
{
  "error": {"code": "RISK_BOUNDARY_EXCEEDED", "message": "max_drawdown_pct exceeded"},
  "correlation_id": "6f1d3b34-...",
  "ts": "2025-08-12T06:58:03Z"
}
```
**代表コード対照表**
| code | HTTP | 再試行方針 |
|---|---:|---|
| `TRADING_PAUSED` | 409 | ❌（解除後に再送） |
| `RISK_BOUNDARY_EXCEEDED` | 422 | ❌（入力/方針見直し） |
| `BROKER_REJECTED` | 424 | ⭕（条件次第で修正） |
| `TIMEOUT_RETRYING` | 504 | ⭕（指数バックオフ） |
| `RATE_LIMITED` | 429 | ⭕（`Retry-After` に従う） |
| `INVALID_REQUEST` | 400 | ❌（修正して再送） |
| `UNAUTHORIZED` | 401 | ❌（認証） |
| `FORBIDDEN` | 403 | ❌（権限） |

### 2.3 ページング & クエリ規約
- `?limit=50&cursor=eyJvZmZzZXQiOjE3Nn0`（**base64url** で安全エンコード）。応答に `next_cursor`  
- フィルタ：`?filter=field:eq:value,field2:in:[a|b]`（簡易 DSL）  
- ソート：`?sort=ts:desc,avg_price:asc`

### 2.4 時刻・数値・精度
- 時刻は**UTC ISO-8601**（`Z` 付き）。  
- 価格/数量/手数料はブローカー仕様に従い**丸め**（`Do-Layer-Contract.md §5.3`）。

---

## 3. ヘルス・メタ
### 3.1 GET `/api/v1/healthz` → 200 OK
### 3.2 GET `/api/v1/version`
```json
{"service":"noctria-api","version":"1.0.0","git":"abc1234","time":"2025-08-12T00:03:21Z"}
```
### 3.3 GET `/api/v1/openapi.json`（自動生成）

---

## 4. Config / Flags / Risk Policy
### 4.1 GET `/api/v1/config`
- 有効コンフィグ（defaults + env + flags の**マージ後**サマリ）。Secrets は伏字。
```json
{"env":"prod","flags":{"global_trading_pause":false,"risk_safemode":true},"etag":"W/\"cfg-abc123\""}
```

### 4.2 PATCH `/api/v1/config/flags`
- 権限：`admin:ops` or `write:config`、**If-Match 必須**
```json
// Request
{"flags":{"global_trading_pause":true}}
// Response
{"ok":true,"flags":{"global_trading_pause":true},"etag":"W/\"cfg-def456\""}
```

### 4.3 GET `/api/v1/config/risk-policy`（`risk_policy.schema.json` 準拠）
### 4.4 PUT `/api/v1/config/risk-policy`（Two-Person + King、If-Match 必須）

---

## 5. Plan APIs
### 5.1 POST `/api/v1/plan/collect`（非同期起動、Airflow 連携）
```json
{"symbols":["BTCUSDT","ETHUSDT"],"timeframe":"5m","from":"2025-08-11","to":"2025-08-12"}
```
→ `{"accepted":true,"job_id":"pdca_plan_workflow:2025-08-12T05:00Z"}`

### 5.2 GET `/api/v1/plan/features`
- `symbol`, `tf`, `at`（スナップ）  
```json
{"meta":{"symbols":["BTCUSDT"],"tf":"5m"},"latest_ts":"2025-08-12T06:55:00Z","signals":{"rsi_14":38.2}}
```

### 5.3 GET `/api/v1/plan/kpi` → `kpi_stats.json`

---

## 6. Do APIs（発注・監査） — *契約詳細は* `./Do-Layer-Contract.md`
### 6.1 POST `/api/v1/do/orders`（Idempotency 必須）
```json
{
  "symbol":"BTCUSDT","side":"BUY","proposed_qty":0.5,
  "max_slippage":0.2,"time":"2025-08-12T06:58:00Z",
  "rationale":"Prometheus signal=+0.8 / vol=mid",
  "meta":{"strategy":"Prometheus-PPO"}
}
```
→ `{"order_id":"SIM-12345","status":"FILLED","avg_price":58999.5,"filled_qty":0.5,"fees":0.12,"ts":"2025-08-12T06:58:03Z"}`

### 6.2 GET `/api/v1/do/executions`（クエリ：`from,to,symbol,strategy,status,limit,cursor`）
- 応答：`exec_result.schema.json` の配列＋`next_cursor`

### 6.3 GET `/api/v1/do/audit/{order_id}` → `audit_order.json`（完全記録）

---

## 7. Check APIs（評価・監視）
### 7.1 POST `/api/v1/check/evaluate`（非同期・Airflow）
```json
{"from":"2025-08-01","to":"2025-08-12","strategies":["Prometheus-PPO"]}
```
→ `{"accepted":true,"job_id":"pdca_check_flow:2025-08-12"}`

### 7.2 GET `/api/v1/check/kpi/summary`（`kpi_summary.schema.json`）
### 7.3 GET `/api/v1/check/alerts/recent`（`risk_event.schema.json` 列挙）

---

## 8. Act APIs（再評価・採用）
### 8.1 POST `/api/v1/act/recheck`（Optuna 等）
```json
{"name":"Prometheus-PPO","config":{"trials":50,"metric":"Sharpe_adj"}}
```

### 8.2 POST `/api/v1/act/adopt`（段階導入、King 承認）
```json
{"name":"Prometheus-PPO","version":"1.2.0",
 "plan":{"stages":[0.07,0.3,1.0],"days_per_stage":3}}
```
→ `{"accepted":true,"release_id":"rel_20250812_001"}`

### 8.3 GET `/api/v1/act/releases`（採用一覧）

---

## 9. Strategies APIs（提案/一覧/状態）
### 9.1 POST `/api/v1/strategies/proposals`（G0 起案）
```json
{"name":"Prometheus-PPO","summary":"PPO policy with volatility-aware reward",
 "kpi_expectation":{"sharpe":[0.9,1.2]}}
```
### 9.2 GET `/api/v1/strategies?state=candidate|shadow|canary|adopted|deprecated`
### 9.3 GET `/api/v1/strategies/{name}`（詳細）

---

## 10. Alerts / Streaming
### 10.1 GET `/api/v1/alerts/stream`（SSE）
- `event: risk_event` / `data: {...}`
- **再接続**：`Last-Event-ID` に対応（`id:` フィールドを送出）

### 10.2 Webhooks（受信）`POST /api/v1/webhooks/broker/execution`
- **署名検証（HMAC-SHA256）**：`X-Noctria-Signature: t=<ts>, v1=<hex>`  
  検証文字列：`"{t}.{raw_body}"` を共有鍵で HMAC。時刻乖離 ±5 分を許容。
```json
{"order_id":"...","status":"FILLED","avg_price":...,"ts":"...","signature":"..."}
```

---

## 11. 運用（Ops）エンドポイント（権限強：`admin:ops`）
### 11.1 POST `/api/v1/ops/trading/pause`
```json
{"pause": true, "reason": "slippage spike", "ttl_minutes": 60}
```
- `ttl_minutes` 超過で自動解除（注釈を残す）

### 11.2 POST `/api/v1/ops/airflow/trigger`
```json
{"dag_id":"pdca_check_flow","conf":{"date":"2025-08-12"}}
```

---

## 12. 契約スキーマ（Schemas）
- **Plan → Do**：`order_request.schema.json`  
- **Do → Check**：`exec_result.schema.json`, `risk_event.schema.json`  
- **Check → Act**：`kpi_summary.schema.json`  
- **Risk Policy**：`risk_policy.schema.json`  
> 実体は `docs/schemas/`。変更時は **Do-Layer-Contract** と**同一PR**で更新。

---

## 13. 例（Examples）
### 13.1 curl：グローバル抑制 ON
```bash
curl -X PATCH https://example/api/v1/config/flags \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H 'If-Match: W/"cfg-abc123"' \
  -H "Content-Type: application/json" \
  -d '{"flags":{"global_trading_pause":true}}'
```

### 13.2 curl：KPI の取得
```bash
curl -s -H "Authorization: Bearer $TOKEN" https://example/api/v1/check/kpi/summary | jq .
```

### 13.3 curl：戦略の段階導入
```bash
curl -X POST https://example/api/v1/act/adopt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{"name":"Prometheus-PPO","version":"1.2.0","plan":{"stages":[0.07,0.3,1.0],"days_per_stage":3}}'
```

---

## 14. セキュリティ & 監査
- **Non-Negotiables**（抜粋）
  1. `risk_policy` 越境を可能にする API は**存在しない**
  2. **Secrets を返す API は禁止**（Vault/ENV のみ）
  3. すべての変更系は **Idempotency-Key 必須**
- **監査**：全リクエストの `method, path, actor, ip, status, correlation_id, body_hash` を記録
- **レート制限**：デフォルト 60 rpm、`/do/orders` は 10 rps（429 は `Retry-After` 付き）

---

## 15. バージョニング & 非推奨（Versioning/Deprecation）
- **パス版**：`/api/v1`（メジャー変更で `/v2`）
- **非推奨告知**：`Deprecation` ヘッダ + `Link: sunset=`、`Release-Notes.md` にも記載
- **後方互換**：POST/PATCH の追加フィールドは**後方互換**のみ

---

## 16. テスト（契約テスト/モック）
- **契約テスト**：`docs/schemas/*.schema.json` に適合（CI 必須）
- **モック**：`/api/v1/_mock/*` は **dev 限定**（本番禁止）

---

## 17. 既知の制約 / TODO
- ブローカー Webhook のレート制限対応（バッチ受信、再送論理）
- SSE 大量イベント時のバックプレッシャ制御（キュー化/ドロップ方針）

---

## 18. 変更履歴（Changelog）
- **2025-08-12**: **v1.1** Idempotency を 24h に統一、`RateLimit-*`/`Retry-After` 追加、`ETag/If-Match` 導入、SSE 再接続と Webhook 署名仕様を明文化、OpenAPI 配布点を追加
- **2025-08-12**: v1.0 初版作成（PDCA/Config/Strategies/Alerts/Ops/契約/安全）
