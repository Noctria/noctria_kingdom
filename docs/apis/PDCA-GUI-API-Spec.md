# PDCA — GUI API 仕様（一覧 / 詳細 / ダウンロード）
**Last Updated:** 2025-08-24 (JST)  
**Owner:** PDCA / Platform

関連文書:
- `docs/apis/PDCA-Recheck-API-Spec.md`
- `docs/airflow/DAG-PDCA-Recheck.md`
- `docs/architecture/schema/PDCA-MetaSchema.md`
- `docs/security/AuthN-AuthZ-DoLayer.md`
- `docs/platform/RateLimit-Quota-DoLayer.md`

---

## 0. 目的
運用者GUIが利用する **読み取り系API** を定義する。  
対象は「戦略一覧/健康状態」「個別詳細」「成果物ダウンロードURL提供」「再チェックの進捗確認」。

---

## 1. 認証・レート
- 認証: **JWT (RS256)** 必須（`aud=pdca.gui`, `iss=noctria.auth`, `sub=client_id`）
- 認可（scope）:
  - `pdca:read`（一覧/詳細/進捗）
  - `pdca:download`（成果物URL 取得）
- Rate（初期）: 600 rpm / client（一覧・詳細合算）
- 監査ログ: `client_id, endpoint, query, rows, trace_id`

---

## 2. エンドポイント概要
| Method | Path | 概要 | 権限 | 成功HTTP |
|---|---|---|---|---|
| GET | `/gui/strategies` | 戦略の一覧（最新健康状態を含む） | `pdca:read` | 200 |
| GET | `/gui/strategies/:id` | 戦略の詳細（直近結果/KPI/履歴） | `pdca:read` | 200 |
| GET | `/gui/strategies/:id/results` | 指定期間のPDCA結果一覧 | `pdca:read` | 200 |
| GET | `/gui/requests/:request_id` | 再チェックリクエストの進捗/集計 | `pdca:read` | 200 |
| GET | `/gui/artifacts/:artifact_id/url` | 成果物の署名付きURLを返す | `pdca:download` | 200 |

---

## 3. パラメータ仕様

### 3.1 `GET /gui/strategies`
- **Query**
  - `q`: 部分一致検索（`id/title`）
  - `tags_any`: CSV（例 `daily,priority`）
  - `health`: CSV（`healthy,degraded,unknown`）
  - `instrument`: CSV（`USDJPY,EURUSD`）
  - `enabled`: `true|false`（既定: both）
  - `sort`: `last_checked_at.desc`（既定）、`id.asc` など
  - `page`: 1〜, 既定=1
  - `page_size`: 10〜100, 既定=50
- **応答（例）**
```json
{
  "items": [
    {
      "id": "strat.meanrev.m1",
      "title": "MeanReversion M1",
      "instrument": "USDJPY",
      "enabled": true,
      "last_health": "healthy",
      "last_checked_at": "2025-08-24T02:33:10Z",
      "tags": ["daily","priority"]
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 127
}
```
- **実装メモ**: `vw_strategy_latest_health` + `strategy_tags` を結合（MetaSchema 参照）

### 3.2 `GET /gui/strategies/:id`
- **Query**
  - `summary_window_days`: 30（既定）— KPI サマリ期間
  - `limit_history`: 50（既定）— 過去結果の最大件数
- **応答（例）**
```json
{
  "strategy": {
    "id": "strat.meanrev.m1",
    "title": "MeanReversion M1",
    "instrument": "USDJPY",
    "enabled": true,
    "health": "healthy",
    "tags": ["daily","priority"],
    "metadata": {"owner":"ops-team"}
  },
  "summary": {
    "window_days": 30,
    "kpi_avg": {"sharpe": 1.1, "winrate": 0.56, "max_dd": 0.08},
    "last_completed_at": "2025-08-24T02:33:10Z"
  },
  "recent_results": [
    {
      "completed_at": "2025-08-24T02:33:10Z",
      "health": "healthy",
      "metrics": {"sharpe": 1.25, "winrate": 0.57, "max_dd": 0.07},
      "result_digest": "sha256:abcd...",
      "request_id": "01JABC...XYZ"
    }
  ],
  "artifacts": [
    {"artifact_id": 123, "kind": "chart", "created_at": "2025-08-24T02:33:11Z"}
  ]
}
```

### 3.3 `GET /gui/strategies/:id/results`
- **Query**
  - `from`: RFC3339
  - `to`: RFC3339
  - `limit`: 200（上限）
- **応答（例）**
```json
{
  "items": [
    {
      "completed_at": "2025-08-23T03:11:00Z",
      "health": "degraded",
      "metrics": {"sharpe": 0.7, "winrate": 0.49, "max_dd": 0.12},
      "result_digest": "sha256:efgh...",
      "request_id": "01JABCP...QRS"
    }
  ]
}
```

### 3.4 `GET /gui/requests/:request_id`
- **説明**: `PDCA-Recheck-API-Spec` の 4.2 と整合。Airflow run の集約ビュー。
- **応答（例）**
```json
{
  "status": "success",
  "request_id": "01JABCXYZ-ULID-5678",
  "submitted_at": "2025-08-24T03:34:56Z",
  "progress": {
    "total_batches": 2,
    "completed_batches": 2,
    "total_strategies": 37,
    "completed_strategies": 37
  },
  "summary": {"success":34,"failed":3,"health":{"healthy":29,"degraded":5,"unknown":3}},
  "artifacts": [
    {"artifact_id": 777, "kind": "report", "created_at": "2025-08-24T03:55:00Z"}
  ],
  "dag": {"name":"pdca_recheck","run_ids":["manual__...__b1","manual__...__b2"]}
}
```

### 3.5 `GET /gui/artifacts/:artifact_id/url`
- **説明**: 署名付きURLを払い出す。実体はS3/MinIO/ローカル。  
- **応答（例）**
```json
{
  "artifact_id": 123,
  "signed_url": "https://minio.local/...&X-Amz-Expires=300",
  "expires_in": 300
}
```

---

## 4. エラー仕様
| HTTP | error | 説明 | 対処 |
|---|---|---|---|
| 400 | `BAD_REQUEST` | パラメータ不正（期間/並び順） | 入力修正 |
| 401 | `UNAUTHORIZED` | JWT 不正/期限切れ | 再認証 |
| 403 | `FORBIDDEN` | scope 不足 | 権限付与 |
| 404 | `NOT_FOUND` | 戦略/成果物なし | ID確認 |
| 429 | `RATE_LIMITED` | 制限超過 | `Retry-After` |
| 500 | `INTERNAL_ERROR` | 予期せぬ異常 | 再試行/問い合わせ |

---

## 5. ソート・ページング
- ソートキー: `last_checked_at`, `id`, `instrument`, `health`
- ページング: `page` & `page_size`（応答に `total` を含める）

---

## 6. 可観測性（API側）
- Logs（JSON）: `endpoint, client_id, page, page_size, rows, latency_ms, trace_id`
- Metrics:
  - `gui.list.requests_total{outcome}`
  - `gui.detail.requests_total{outcome}`
  - `gui.download.requests_total{outcome}`
  - `gui.api.latency_ms{endpoint}`

---

## 7. セキュリティ
- `artifact` のURLは**署名付き・短命（既定 300s）**
- `q`（検索語）はサニタイズ（SQLワイルドカード注入に注意）
- レスポンスに**機微情報を含めない**（内部ID/秘密タグを除外）

---

## 8. 実装メモ（DBクエリ）
- 一覧: `vw_strategy_latest_health` を基に `strategy_tags` でフィルタ  
- 詳細: `pdca_results` を `completed_at DESC` で上位 N 件、`artifacts` も同様  
- 期間検索: `pdca_results.completed_at BETWEEN $from AND $to`

---

## 9. 例: curl
```bash
# 一覧
curl -s "http://localhost:8001/gui/strategies?tags_any=daily&health=healthy&sort=last_checked_at.desc&page=1&page_size=50" \
 -H "Authorization: Bearer $JWT"

# 詳細
curl -s "http://localhost:8001/gui/strategies/strat.meanrev.m1?summary_window_days=30&limit_history=20" \
 -H "Authorization: Bearer $JWT"

# 成果物URL
curl -s "http://localhost:8001/gui/artifacts/123/url" \
 -H "Authorization: Bearer $JWT"
```

---

## 10. 変更履歴
- **2025-08-24**: 初版（一覧/詳細/結果/リクエスト/ダウンロード）
