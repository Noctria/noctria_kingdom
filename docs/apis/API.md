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

<!-- AUTOGEN:CHANGELOG START -->

### 🛠 Updates since: `2025-08-12 09:22 UTC`

- `4715c7b` 2025-08-15T05:12:32+09:00 — **Update update_docs_from_index.py** _(by Noctoria)_
  - `scripts/update_docs_from_index.py`
- `c20a9bd` 2025-08-15T04:58:31+09:00 — **Create update_docs_from_index.py** _(by Noctoria)_
  - `scripts/update_docs_from_index.py`
- `969f987` 2025-08-15T04:36:32+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `a39c7db` 2025-08-15T04:14:15+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `09a3e13` 2025-08-15T03:51:14+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `aea152c` 2025-08-15T03:34:12+09:00 — **Update strategy_detail.py** _(by Noctoria)_
  - `noctria_gui/routes/strategy_detail.py`
- `3bc997c` 2025-08-15T03:23:40+09:00 — **Update strategy_detail.py** _(by Noctoria)_
  - `noctria_gui/routes/strategy_detail.py`
- `482da8a` 2025-08-15T03:02:26+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `feef06f` 2025-08-15T02:33:44+09:00 — **Update docker-compose.yaml** _(by Noctoria)_
  - `airflow_docker/docker-compose.yaml`
- `e4e3005` 2025-08-15T02:15:13+09:00 — **Update __init__.py** _(by Noctoria)_
  - `noctria_gui/__init__.py`
- `4b38d3b` 2025-08-15T01:48:52+09:00 — **Update path_config.py** _(by Noctoria)_
  - `src/core/path_config.py`
- `00fc537` 2025-08-15T01:44:12+09:00 — **Create kpi_minidemo.py** _(by Noctoria)_
  - `src/plan_data/kpi_minidemo.py`
- `daa5865` 2025-08-15T01:37:54+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `5e52eca` 2025-08-15T01:35:28+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `e320246` 2025-08-15T01:34:39+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `de39f94` 2025-08-15T01:33:29+09:00 — **Create Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `e4c82d5` 2025-08-15T01:16:27+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `47a5847` 2025-08-15T01:06:11+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `15188ea` 2025-08-15T00:59:08+09:00 — **Update __init__.py** _(by Noctoria)_
  - `noctria_gui/__init__.py`
- `1b4c2ec` 2025-08-15T00:41:34+09:00 — **Create statistics_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/statistics_routes.py`
- `49795a6` 2025-08-15T00:34:44+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `4d7dd70` 2025-08-15T00:28:18+09:00 — **Update act_service.py** _(by Noctoria)_
  - `src/core/act_service.py`
- `1d38c3c` 2025-08-14T22:21:33+09:00 — **Create policy_engine.py** _(by Noctoria)_
  - `src/core/policy_engine.py`
- `dcdd7f4` 2025-08-14T22:15:59+09:00 — **Update airflow_client.py** _(by Noctoria)_
  - `src/core/airflow_client.py`
- `e66ac97` 2025-08-14T22:08:25+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `6c49b8e` 2025-08-14T21:58:17+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `e0b9eaa` 2025-08-14T21:53:00+09:00 — **Update pdca_summary_service.py** _(by Noctoria)_
  - `src/plan_data/pdca_summary_service.py`
- `368203e` 2025-08-14T21:44:48+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `cc9da23` 2025-08-14T21:32:42+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `434d2e2` 2025-08-14T21:23:55+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `d0df823` 2025-08-14T21:18:54+09:00 — **Update decision_registry.py** _(by Noctoria)_
  - `src/core/decision_registry.py`
- `1eaed26` 2025-08-14T21:08:01+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `b557920` 2025-08-14T21:03:59+09:00 — **Update strategy_evaluator.py** _(by Noctoria)_
  - `src/core/strategy_evaluator.py`
- `0c7a12f` 2025-08-14T21:00:00+09:00 — **Create decision_registry.py** _(by Noctoria)_
  - `src/core/decision_registry.py`
- `2f034a5` 2025-08-14T20:58:16+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `28bb890` 2025-08-14T20:51:37+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `307da2d` 2025-08-14T20:49:15+09:00 — **Create act_service.py** _(by Noctoria)_
  - `src/core/act_service.py`
- `bf993f3` 2025-08-14T20:41:12+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `4b7ca22` 2025-08-14T20:35:18+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `3880c7b` 2025-08-14T20:32:42+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `074b6cf` 2025-08-14T20:24:03+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `46d639d` 2025-08-14T20:17:49+09:00 — **Update strategy_evaluator.py** _(by Noctoria)_
  - `src/core/strategy_evaluator.py`
- `f63e897` 2025-08-14T20:12:50+09:00 — **Update veritas_recheck_dag.py** _(by Noctoria)_
  - `airflow_docker/dags/veritas_recheck_dag.py`
- `7c3785e` 2025-08-14T20:08:26+09:00 — **Create veritas_recheck_all_dag.py** _(by Noctoria)_
  - `airflow_docker/dags/veritas_recheck_all_dag.py`
- `49fe520` 2025-08-14T15:41:00+09:00 — **main.py を更新** _(by Noctoria)_
  - `noctria_gui/main.py`
- `3648612` 2025-08-14T15:35:27+09:00 — **pdca_routes.py を更新** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `f7f1972` 2025-08-14T06:32:19+09:00 — **Update base_hud.html** _(by Noctoria)_
  - `noctria_gui/templates/base_hud.html`
- `eae18c6` 2025-08-14T06:21:35+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `1d6047c` 2025-08-14T06:10:33+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `3c55ed0` 2025-08-14T06:04:20+09:00 — **Create dammy** _(by Noctoria)_
  - `noctria_gui/static/vendor/dammy`
- `7b4624d` 2025-08-14T05:45:03+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `35e4c50` 2025-08-14T04:49:16+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `6c88b9f` 2025-08-14T04:31:58+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `1a0b00e` 2025-08-14T04:29:17+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `2b51ef9` 2025-08-14T04:27:11+09:00 — **Create pdca_summary_service.py** _(by Noctoria)_
  - `src/plan_data/pdca_summary_service.py`
- `6ff093a` 2025-08-14T04:24:34+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `7e2e056` 2025-08-14T04:20:51+09:00 — **Create pdca_control.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_control.html`
- `cf248ee` 2025-08-14T04:15:18+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `d8e0d6e` 2025-08-14T04:12:02+09:00 — **Create airflow_client.py** _(by Noctoria)_
  - `src/core/airflow_client.py`
- `b2aa77a` 2025-08-14T01:09:50+09:00 — **Update pdca_latency_daily.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_latency_daily.html`
- `38a01da` 2025-08-14T01:06:15+09:00 — **Update pdca_timeline.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_timeline.html`
- `303f8d2` 2025-08-14T01:02:09+09:00 — **Update observability.py** _(by Noctoria)_
  - `noctria_gui/routes/observability.py`
- `206dac2` 2025-08-14T00:21:25+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `c08e345` 2025-08-13T23:37:10+09:00 — **Update init_obs_schema.sql** _(by Noctoria)_
  - `scripts/init_obs_schema.sql`
- `00df80a` 2025-08-13T23:18:49+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `f08d9c2` 2025-08-13T23:12:35+09:00 — **Create init_obs_schema.sql** _(by Noctoria)_
  - `scripts/init_obs_schema.sql`
- `a021461` 2025-08-13T22:07:03+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `d1e0cd2` 2025-08-13T22:01:43+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `435b19e` 2025-08-13T21:57:54+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `82cc0ad` 2025-08-13T16:33:01+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `c42088c` 2025-08-13T16:29:45+09:00 — **Update observability.py** _(by Noctoria)_
  - `noctria_gui/routes/observability.py`
- `5cfbeff` 2025-08-13T16:15:55+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `8c5b055` 2025-08-13T16:11:34+09:00 — **Create pdca_latency_daily.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_latency_daily.html`
- `f8c1e9a` 2025-08-13T16:10:52+09:00 — **Create pdca_timeline.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_timeline.html`
- `3bc104a` 2025-08-13T16:07:38+09:00 — **Create observability.py** _(by Noctoria)_
  - `noctria_gui/routes/observability.py`
- `b1453a0` 2025-08-13T16:03:47+09:00 — **Update order_execution.py** _(by Noctoria)_
  - `src/execution/order_execution.py`
- `9ed85b3` 2025-08-13T15:53:16+09:00 — **Update risk_policy.py** _(by Noctoria)_
  - `src/execution/risk_policy.py`
- `b112ce9` 2025-08-13T15:30:22+09:00 — **Update contracts.py** _(by Noctoria)_
  - `src/plan_data/contracts.py`
- `fba6dda` 2025-08-13T15:24:26+09:00 — **Update risk_gate.py** _(by Noctoria)_
  - `src/execution/risk_gate.py`
- `112e173` 2025-08-13T15:18:00+09:00 — **Create risk_policy.py** _(by Noctoria)_
  - `src/execution/risk_policy.py`
- `99a3122` 2025-08-13T14:53:14+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `9786e16` 2025-08-13T14:49:18+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `3696066` 2025-08-13T14:45:26+09:00 — **Create show_timeline.py** _(by Noctoria)_
  - `src/tools/show_timeline.py`
- `dee8185` 2025-08-13T14:38:49+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `a33f63e` 2025-08-13T14:17:31+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `3fe7a25` 2025-08-13T13:42:41+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `aa30bc6` 2025-08-13T13:33:25+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `7b71201` 2025-08-13T13:30:05+09:00 — **Update path_config.py** _(by Noctoria)_
  - `src/core/path_config.py`
- `8305919` 2025-08-13T13:22:29+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `be7bfa6` 2025-08-13T13:16:51+09:00 — **Create __init__.py** _(by Noctoria)_
  - `src/strategies/__init__.py`
- `7aa58ce` 2025-08-13T13:16:23+09:00 — **Create __init__.py** _(by Noctoria)_
  - `src/e2e/__init__.py`
- `70d8587` 2025-08-13T13:16:11+09:00 — **Create __init__.py** _(by Noctoria)_
  - `src/decision/__init__.py`
- `14a5297` 2025-08-13T13:14:58+09:00 — **Update __init__.py** _(by Noctoria)_
  - `src/__init__.py`
- `e331d07` 2025-08-13T13:12:08+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `4567802` 2025-08-13T13:09:30+09:00 — **Update __init__.py** _(by Noctoria)_
  - `src/__init__.py`
- `4a02589` 2025-08-13T13:06:52+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `b9c0561` 2025-08-13T12:58:07+09:00 — **Update decision_engine.py** _(by Noctoria)_
  - `src/decision/decision_engine.py`
- `7913390` 2025-08-13T12:55:44+09:00 — **Create profile_loader.py** _(by Noctoria)_
  - `src/plan_data/profile_loader.py`
- `e29e4bb` 2025-08-13T12:50:28+09:00 — **Create risk_gate.py** _(by Noctoria)_
  - `src/execution/risk_gate.py`
- `5c617c4` 2025-08-13T12:43:52+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `44bc542` 2025-08-13T11:26:05+09:00 — **Update decision_engine.py** _(by Noctoria)_
  - `src/decision/decision_engine.py`
- `8b7bc76` 2025-08-13T11:24:48+09:00 — **Rename decision_engine.py to decision_engine.py** _(by Noctoria)_
  - `src/decision/decision_engine.py`
- `e70244e` 2025-08-13T11:23:29+09:00 — **Rename trace.py to trace.py** _(by Noctoria)_
  - `src/core/trace.py`
- `7dfab9c` 2025-08-13T11:17:32+09:00 — **Update trace.py** _(by Noctoria)_
  - `src/plan_data/trace.py`
- `735a519` 2025-08-13T11:02:21+09:00 — **Create decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `e4a9e83` 2025-08-13T10:58:32+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `9c1c5d0` 2025-08-13T10:50:29+09:00 — **Update decision_engine.py** _(by Noctoria)_
  - `src/plan_data/decision_engine.py`
- `31a28ae` 2025-08-13T10:47:02+09:00 — **Update trace.py** _(by Noctoria)_
  - `src/plan_data/trace.py`
- `c7c65fb` 2025-08-13T04:55:43+09:00 — **Update plan_to_all_minidemo.py** _(by Noctoria)_
  - `src/plan_data/plan_to_all_minidemo.py`
- `4ee7b2c` 2025-08-13T04:33:54+09:00 — **Update utils.py** _(by Noctoria)_
  - `src/core/utils.py`
- `7a72c02` 2025-08-13T04:26:01+09:00 — **Update aurus_singularis.py** _(by Noctoria)_
  - `src/strategies/aurus_singularis.py`
- `9738c0b` 2025-08-13T04:18:54+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `668d424` 2025-08-13T04:07:33+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `f06ae54` 2025-08-13T03:05:40+09:00 — **Update plan_to_all_minidemo.py** _(by Noctoria)_
  - `src/plan_data/plan_to_all_minidemo.py`
- `831ff6c` 2025-08-13T02:53:37+09:00 — **Create strategy_adapter.py** _(by Noctoria)_
  - `src/plan_data/strategy_adapter.py`
- `43c5d7a` 2025-08-13T02:53:07+09:00 — **Update trace.py** _(by Noctoria)_
  - `src/plan_data/trace.py`
- `fc92ef5` 2025-08-13T02:50:18+09:00 — **Update analyzer.py** _(by Noctoria)_
  - `src/plan_data/analyzer.py`
- `76795bf` 2025-08-13T02:47:28+09:00 — **Update statistics.py** _(by Noctoria)_
  - `src/plan_data/statistics.py`
- `af4106e` 2025-08-13T02:44:27+09:00 — **Update features.py** _(by Noctoria)_
  - `src/plan_data/features.py`
- `34e7328` 2025-08-13T02:40:33+09:00 — **Update collector.py** _(by Noctoria)_
  - `src/plan_data/collector.py`
- `b80bcf2` 2025-08-13T02:24:16+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `386097b` 2025-08-13T01:53:40+09:00 — **Create ai_adapter.py** _(by Noctoria)_
  - `src/plan_data/ai_adapter.py`
- `881c42c` 2025-08-13T01:52:58+09:00 — **Create observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `04080ca` 2025-08-13T01:52:28+09:00 — **Create trace.py** _(by Noctoria)_
  - `src/plan_data/trace.py`
- `2f52073` 2025-08-13T01:52:00+09:00 — **Create decision_engine.py** _(by Noctoria)_
  - `src/plan_data/decision_engine.py`
- `e40ac8c` 2025-08-13T01:50:14+09:00 — **Create quality_gate.py** _(by Noctoria)_
  - `src/plan_data/quality_gate.py`
- `1de46ad` 2025-08-13T01:49:35+09:00 — **Create contracts.py** _(by Noctoria)_
  - `src/plan_data/contracts.py`

<!-- AUTOGEN:CHANGELOG END -->
<!-- AUTODOC:BEGIN mode=git_log path_globs="noctria_gui/routes/**/*.py;noctria_gui/**/main.py;src/apis/**/*.py" title="API/GUI Routes 更新履歴（最近30）" limit=30 since=2025-08-01 -->
### API/GUI Routes 更新履歴（最近30）

- **c255eee** 2025-08-17T21:39:52+09:00 — Update airflow_runs.py (by Noctoria)
  - `noctria_gui/routes/airflow_runs.py`
- **7bf9583** 2025-08-17T21:37:22+09:00 — Update decision_registry.py (by Noctoria)
  - `noctria_gui/routes/decision_registry.py`
- **02911c7** 2025-08-16T05:35:57+09:00 — Update main.py (by Noctoria)
  - `noctria_gui/main.py`
- **e38a43b** 2025-08-16T05:34:25+09:00 — Create adoptions.py (by Noctoria)
  - `noctria_gui/routes/adoptions.py`
- **c443b6f** 2025-08-16T05:30:21+09:00 — Update main.py (by Noctoria)
  - `noctria_gui/main.py`
- **0942e18** 2025-08-16T05:20:42+09:00 — Update main.py (by Noctoria)
  - `noctria_gui/main.py`
- **167026b** 2025-08-16T05:19:37+09:00 — Update main.py (by Noctoria)
  - `noctria_gui/main.py`
- **7cfac08** 2025-08-16T05:16:27+09:00 — Create git_tags.py (by Noctoria)
  - `noctria_gui/routes/git_tags.py`
- **2468338** 2025-08-16T04:31:06+09:00 — Update main.py (by Noctoria)
  - `noctria_gui/main.py`
- **a4aafe8** 2025-08-16T04:28:23+09:00 — Create airflow_runs.py (by Noctoria)
  - `noctria_gui/routes/airflow_runs.py`
- **48930df** 2025-08-16T04:26:38+09:00 — Update main.py (by Noctoria)
  - `noctria_gui/main.py`
- **8c40178** 2025-08-16T04:24:43+09:00 — Create decision_registry.py (by Noctoria)
  - `noctria_gui/routes/decision_registry.py`
- **f6b46c9** 2025-08-16T04:23:05+09:00 — Update main.py (by Noctoria)
  - `noctria_gui/main.py`
- **461c74c** 2025-08-16T04:20:33+09:00 — Create act_adopt.py (by Noctoria)
  - `noctria_gui/routes/act_adopt.py`
- **969f987** 2025-08-15T04:36:32+09:00 — Update pdca_summary.py (by Noctoria)
  - `noctria_gui/routes/pdca_summary.py`
- **aea152c** 2025-08-15T03:34:12+09:00 — Update strategy_detail.py (by Noctoria)
  - `noctria_gui/routes/strategy_detail.py`
- **3bc997c** 2025-08-15T03:23:40+09:00 — Update strategy_detail.py (by Noctoria)
  - `noctria_gui/routes/strategy_detail.py`
- **482da8a** 2025-08-15T03:02:26+09:00 — Update pdca_recheck.py (by Noctoria)
  - `noctria_gui/routes/pdca_recheck.py`
- **e4c82d5** 2025-08-15T01:16:27+09:00 — Update pdca_recheck.py (by Noctoria)
  - `noctria_gui/routes/pdca_recheck.py`
- **47a5847** 2025-08-15T01:06:11+09:00 — Update main.py (by Noctoria)
  - `noctria_gui/main.py`
- **1b4c2ec** 2025-08-15T00:41:34+09:00 — Create statistics_routes.py (by Noctoria)
  - `noctria_gui/routes/statistics_routes.py`
- **49795a6** 2025-08-15T00:34:44+09:00 — Update pdca_recheck.py (by Noctoria)
  - `noctria_gui/routes/pdca_recheck.py`
- **e66ac97** 2025-08-14T22:08:25+09:00 — Update pdca_recheck.py (by Noctoria)
  - `noctria_gui/routes/pdca_recheck.py`
- **6c49b8e** 2025-08-14T21:58:17+09:00 — Update pdca_summary.py (by Noctoria)
  - `noctria_gui/routes/pdca_summary.py`
- **368203e** 2025-08-14T21:44:48+09:00 — Update pdca_summary.py (by Noctoria)
  - `noctria_gui/routes/pdca_summary.py`
- **cc9da23** 2025-08-14T21:32:42+09:00 — Update pdca_routes.py (by Noctoria)
  - `noctria_gui/routes/pdca_routes.py`
- **434d2e2** 2025-08-14T21:23:55+09:00 — Update pdca_routes.py (by Noctoria)
  - `noctria_gui/routes/pdca_routes.py`
- **1eaed26** 2025-08-14T21:08:01+09:00 — Update pdca_routes.py (by Noctoria)
  - `noctria_gui/routes/pdca_routes.py`
- **28bb890** 2025-08-14T20:51:37+09:00 — Update pdca_routes.py (by Noctoria)
  - `noctria_gui/routes/pdca_routes.py`
- **4b7ca22** 2025-08-14T20:35:18+09:00 — Update pdca_routes.py (by Noctoria)
  - `noctria_gui/routes/pdca_routes.py`
<!-- AUTODOC:END -->
