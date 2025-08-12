# 🔌 Noctria Kingdom API — Specification

**Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の PDCA（Plan/Do/Check/Act）および運用を支える **統一API** の仕様を定義する。  
> 参照：`../governance/Vision-Governance.md` / `../operations/Runbooks.md` / `../operations/Config-Registry.md` / `../operations/Airflow-DAGs.md` / `../security/Security-And-Access.md` / `./Do-Layer-Contract.md` / `../schemas/*.schema.json`

---

## 0. 概要（Overview）
- **Base URL**：`/api/v1`（内部/外部で同一パス。外部公開はゲート越し）  
- **設計原則**：安全（ガードレール遵守）、監査可能（全操作に証跡）、少数で一貫したモデル  
- **領域**：`/plan`, `/do`, `/check`, `/act`, `/strategies`, `/config`, `/alerts`, `/ops`  

---

## 1. 認証・認可（AuthN/Z）
- **Auth**：`Authorization: Bearer <token>`（OIDC/JWT） or `Authorization: Noctria-Token <key>`（内部）  
- **Scopes（例）**  
  - `read:pdca`, `write:pdca`, `read:orders`, `write:orders`, `read:config`, `write:config`, `admin:ops`  
- **ロール（参考）**：`ops`, `risk`, `models`, `readonly`（詳細は `../security/Security-And-Access.md`）  
- **二要素**：GUI経由操作は 2FA 推奨（`Config-Registry.md` の `gui.auth`）

---

## 2. 共通仕様（Conventions）
- **Headers**
  - `Idempotency-Key`: 書き込み系は**必須**（重複防止、365日キャッシュ）  
  - `X-Correlation-ID`: トレースID（未指定時は自動採番）
  - `Content-Type: application/json; charset=utf-8`
- **エラー**
  ```json
  {
    "error": {"code": "RISK_BOUNDARY_EXCEEDED", "message": "max_drawdown_pct exceeded"},
    "correlation_id": "6f1d3b34-..."
  }
  ```
- **ページング**：`?limit=50&cursor=...`（`next_cursor` を返却）  
- **時間**：全て **UTC ISO-8601**（例：`2025-08-12T06:55:00Z`）  
- **スキーマ**：`docs/schemas/*.schema.json` を正とする（例：`order_request.schema.json`）

---

## 3. ヘルス・メタ
### 3.1 GET `/api/v1/healthz`
- 200 OK（内部依存の軽量チェック）

### 3.2 GET `/api/v1/version`
- 返却例
  ```json
  {"service":"noctria-api","version":"1.0.0","git":"abc1234","time":"2025-08-12T00:03:21Z"}
  ```

---

## 4. Config / Flags / Risk Policy
### 4.1 GET `/api/v1/config`
- 説明：有効コンフィグ（defaults + env + flags の**マージ後**サマリ）。Secrets は伏字。
- 応答（抜粋）
  ```json
  {"env":"prod","flags":{"global_trading_pause":false,"risk_safemode":true}}
  ```

### 4.2 PATCH `/api/v1/config/flags`
- 権限：`admin:ops` or `write:config`  
- リクエスト
  ```json
  {"flags":{"global_trading_pause":true}}
  ```
- 応答
  ```json
  {"ok":true,"flags":{"global_trading_pause":true}}
  ```

### 4.3 GET `/api/v1/config/risk-policy`
- 返却：`risk_policy.schema.json` に適合

---

## 5. Plan APIs
### 5.1 POST `/api/v1/plan/collect`
- 目的：収集～特徴量生成の**非同期起動**。実体は Airflow トリガ。  
- リクエスト
  ```json
  {"symbols":["BTCUSDT","ETHUSDT"],"timeframe":"5m","from":"2025-08-11","to":"2025-08-12"}
  ```
- 応答
  ```json
  {"accepted":true,"job_id":"pdca_plan_workflow:2025-08-12T05:00Z"}
  ```

### 5.2 GET `/api/v1/plan/features`
- クエリ：`symbol`, `tf`, `at`（スナップ時刻）  
- 応答（`features_dict.json` の一部）
  ```json
  {"meta":{"symbols":["BTCUSDT"],"tf":"5m"},"latest_ts":"2025-08-12T06:55:00Z","signals":{"rsi_14":38.2}}
  ```

### 5.3 GET `/api/v1/plan/kpi`
- 返却：`kpi_stats.json`（市場KPIのスナップ）

---

## 6. Do APIs（発注・監査）
> **契約詳細は別紙**：`./Do-Layer-Contract.md`（必読）

### 6.1 POST `/api/v1/do/orders`
- 目的：**提案オーダー**を受け付け、ブローカーへルーティング。Noctus 境界を**厳格適用**。  
- リクエスト（`order_request.schema.json` 準拠）
  ```json
  {
    "symbol":"BTCUSDT","side":"BUY","proposed_qty":0.5,
    "max_slippage":0.2,"time":"2025-08-12T06:58:00Z",
    "rationale":"Prometheus signal=+0.8 / vol=mid","meta":{"strategy":"Prometheus-PPO"}
  }
  ```
- 応答（概略）
  ```json
  {"order_id":"SIM-12345","status":"FILLED","avg_price":58999.5,"filled_qty":0.5,"fees":0.12,"ts":"2025-08-12T06:58:03Z"}
  ```
- 代表エラー
  - `RISK_BOUNDARY_EXCEEDED`（Noctus）  
  - `TRADING_PAUSED`（全局停止中）  
  - `BROKER_REJECTED`

### 6.2 GET `/api/v1/do/executions`
- クエリ：`from`, `to`, `symbol`, `strategy`, `status`  
- 応答：`exec_result.schema.json` の配列

### 6.3 GET `/api/v1/do/audit/{order_id}`
- 応答：`audit_order.json`（監査用完全記録）

---

## 7. Check APIs（評価・監視）
### 7.1 POST `/api/v1/check/evaluate`
- 目的：指定期間の KPI 再計算（非同期・Airflow経由可）  
- リクエスト
  ```json
  {"from":"2025-08-01","to":"2025-08-12","strategies":["Prometheus-PPO"]}
  ```
- 応答
  ```json
  {"accepted":true,"job_id":"pdca_check_flow:2025-08-12"}
  ```

### 7.2 GET `/api/v1/check/kpi/summary`
- 応答：`kpi_summary.schema.json` 準拠

### 7.3 GET `/api/v1/check/alerts/recent`
- 応答：直近の `risk_event.json`（`risk_event.schema.json` 準拠）の列挙

---

## 8. Act APIs（再評価・採用）
### 8.1 POST `/api/v1/act/recheck`
- 目的：候補戦略の**再評価**を起動（Optuna など）。  
- リクエスト
  ```json
  {"name":"Prometheus-PPO","config":{"trials":50,"metric":"Sharpe_adj"}}
  ```

### 8.2 POST `/api/v1/act/adopt`
- 目的：**段階導入**の開始（7%→30%→100%）。King 承認が必要。  
- リクエスト
  ```json
  {"name":"Prometheus-PPO","version":"1.2.0","plan":{"stages":[0.07,0.3,1.0],"days_per_stage":3}}
  ```
- 応答
  ```json
  {"accepted":true,"release_id":"rel_20250812_001"}
  ```

### 8.3 GET `/api/v1/act/releases`
- 応答：採用済み戦略の一覧（`strategy_release.json` の配列）

---

## 9. Strategies APIs（提案/一覧/状態）
### 9.1 POST `/api/v1/strategies/proposals`
- 目的：新規戦略候補の起案（G0）  
- リクエスト（抜粋）
  ```json
  {"name":"Prometheus-PPO","summary":"PPO policy with volatility-aware reward","kpi_expectation":{"sharpe":[0.9,1.2]}}
  ```

### 9.2 GET `/api/v1/strategies`
- クエリ：`state=candidate|shadow|canary|adopted|deprecated`  
- 応答：戦略の軽量メタ一覧

### 9.3 GET `/api/v1/strategies/{name}`
- 応答：戦略詳細（最新バージョン、状態、配分、関連モデル等）

---

## 10. Alerts / Streaming
### 10.1 GET `/api/v1/alerts/stream`（SSE）
- タイプ：`text/event-stream`  
- 例：`event: risk_event` / `data: {"kind":"LOSING_STREAK","severity":"HIGH",...}`

### 10.2 Webhooks（受信）
- `POST /api/v1/webhooks/broker/execution`（署名検証）  
  ```json
  {"order_id":"...","status":"FILLED","avg_price":...,"ts":"...","signature":"..."}
  ```

---

## 11. 運用（Ops）エンドポイント
> **権限強**：`admin:ops` が必要。GUI ボタンの裏側でのみ使用想定。

### 11.1 POST `/api/v1/ops/trading/pause`
```json
{"pause": true, "reason": "slippage spike", "ttl_minutes": 60}
```

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
> 実体は `docs/schemas/`。変更時は `./Do-Layer-Contract.md` と整合必須。

---

## 13. 例（Examples）

### 13.1 curl：グローバル抑制 ON
```bash
curl -X PATCH https://example/api/v1/config/flags \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
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
  -d '{"name":"Prometheus-PPO","version":"1.2.0","plan":{"stages":[0.07,0.3,1.0],"days_per_stage":3}}'
```

---

## 14. セキュリティ & 監査
- **Non-Negotiables**（抜粋）
  1. `risk_policy` 越境を可能にする API は**存在しない**  
  2. **Secrets を返す API は禁止**。Vault/ENV 経由のみ  
  3. すべての変更系は **Idempotency-Key 必須**  
- **監査**：全リクエストの `method, path, actor, ip, status, correlation_id, body_hash` を記録  
- **レート制限**：デフォルト 60 rpm / `do_layer_flow` 系は 10 rps（調整可）

---

## 15. バージョニング & 非推奨（Versioning/Deprecation）
- **パス版**：`/api/v1`（メジャー変更で `/v2`）  
- **非推奨告知**：レスポンス `Deprecation` ヘッダと `Link: sunset=` を返却、`Release-Notes.md` に告知  
- **下位互換**：PATCH/POST の追加フィールドは原則**後方互換**

---

## 16. テスト（契約テスト/モック）
- **契約テスト**：`Do-Layer-Contract.md` に沿った JSON Schema 検証を CI に組み込み  
- **モック**：`/api/v1/_mock/*` は `dev` のみ有効（本番禁止）

---

## 17. 既知の制約 / TODO
- ブローカー Webhook のレート制限対応（バッチ受信）  
- SSE での大量イベント時のバックプレッシャ制御

---

## 18. 変更履歴（Changelog）
- **2025-08-12**: 初版作成（PDCA/Config/Strategies/Alerts/Ops/契約/安全）

