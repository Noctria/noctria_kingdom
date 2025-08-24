# PDCA API — 横断設計ガイド（設計規約 / 幂等 / 正規化 / エラー / ページング）
**Status:** Stable Candidate  
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Platform / PDCA

関連文書:
- `docs/apis/openapi/pdca-api.yaml`（機械可読仕様のソース）
- `docs/apis/PDCA-Recheck-API-Spec.md`（機能別詳細）
- `docs/apis/PDCA-GUI-API-Spec.md`（GUI向け）
- `docs/integration/Airflow-RestAdapter-Design.md`
- `docs/architecture/schema/PDCA-MetaSchema.md`

---

## 0. 目的
本ドキュメントは **OpenAPI を補完**し、API実装/運用で迷わないための**横断規約**を定義する。
- 設計原則（互換性・命名・日付/ID）
- **幂等化**（Idempotency-Key）と**ボディ正規化**（digest 算出）
- エラーモデル & **エラーカタログ**
- ページング/ソート/フィルタ
- レート制限/セキュリティ/サイズ制限
- 例・チェックリスト

---

## 1. 設計原則
1. **後方互換最優先**：既存クライアントが壊れない変更のみを既定とする。  
2. **明示の互換契約**：Breaking 変更は **新しいフィールド追加**や **別エンドポイント**で提供。  
3. **機械可読が一次情報**：OpenAPI（YAML）が唯一の契約。Markdownは解説。  
4. **時刻は RFC3339 / UTC**：`"2025-08-24T03:34:56Z"` を基本。GUI表示はJSTだがAPIはUTC。  
5. **IDは可搬・可視**：`request_id` は **ULID** 推奨（もしくはUUID v4）。URLに出してOK。  
6. **リソース命名**：英小文字+`[._-]`。例：`strat.meanrev.m1`。  

---

## 2. バージョニング
- **URLにバージョンは持たない**（現時点）。後方互換が崩れる場合は `/v2` を導入。  
- **OpenAPI `info.version`** と **変更履歴**で管理。  
- **フィールドの追加**は*後方互換*。**削除/型変更**は*破壊的*（避ける）。

---

## 3. ヘッダ規約（共通）
| ヘッダ | 方向 | 説明 |
|---|---|---|
| `Authorization: Bearer <JWT>` | Req | 認証（`aud=pdca|pdca.gui`, `iss=noctria.auth`） |
| `Idempotency-Key: <ULID/UUID>` | Req(POST再チェック系) | **必須**（重複抑止）。`/pdca/recheck*` |
| `Content-Type: application/json` | Req/Res | JSONのみ |
| `X-Request-Id: <ULID>` | Res | サーバ側生成のトレースID（ログ相関用） |
| `Retry-After: <sec>` | Res | 429時の再試行秒数 |

---

## 4. 認証・認可
- **JWT (RS256)**：`aud` に `pdca`（書き系）/`pdca.gui`（読み系）。  
- **Scopes**：  
  - 読み取り：`pdca:read`  
  - 再チェック：`pdca:recheck` / 一括 `pdca:recheck_all`  
  - ダウンロードURL：`pdca:download`  
- **推奨クレーム**：`sub`（client_id）、`exp`、`iat`、`scope`。

---

## 5. 幂等（Idempotency）とボディ正規化
### 5.1 ポリシー
- `/pdca/recheck` と `/pdca/recheck_all` は **冪等要求**。  
- クライアントは **毎リクエストに `Idempotency-Key`** を付与。  
- サーバは **「正規化ボディのダイジェスト」** + `Idempotency-Key` で重複判定。  
  - **完全一致** → 既存 `request_id` を返す（202）。  
  - **差分あり** → **409 `IDEMPOTENCY_CONFLICT`**。

### 5.2 正規化（Canonical JSON）アルゴリズム
1. **キー順序**：辞書順で再帰ソート。  
2. **ホワイトスペース**：全削除（最小表現）。  
3. **数値**：`JSON`の数値表現（不要な `.0` を避け、小数はそのまま）。  
4. **真偽/NULL**：`true/false/null`。  
5. **配列順**：入力順を保持（意味順序があるため）。  
6. **文字列**：Unicode 正規化（NFC）推奨。  
7. **除外キー**：`trace_id` のような**非同一性キー**は digest 対象から除外可（仕様に明記）。

**擬似コード（説明用）**：
```python
def canonicalize(obj):
    if isinstance(obj, dict):
        return {k: canonicalize(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        return [canonicalize(x) for x in obj]
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    return obj  # numbers, bool, None

def digest(obj):
    canon = json.dumps(canonicalize(obj), ensure_ascii=False, separators=(",",":"))
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()
```

---

## 6. エラーモデル & カタログ
### 6.1 エラーモデル（固定）
```json
{ "error": "BAD_REQUEST", "message": "window is invalid", "retry_after": 12? }
```
- `error` は **列挙子**。`message` は人間可読（英語ベース推奨）。`retry_after` は 429 のみ。

### 6.2 カタログ（最小核）
| HTTP | error | 代表原因 | 備考 |
|---|---|---|---|
| 400 | `BAD_REQUEST` | パラメータ/バリデーション失敗 | OpenAPIに準拠、詳細は `message` |
| 401 | `UNAUTHORIZED` | JWT 不備 | 署名/exp/aud/iss/スコープ欠落 |
| 403 | `FORBIDDEN` | スコープ不足 | `pdca:recheck_all` なし等 |
| 404 | `NOT_FOUND` | リソース不存在 | id, request_id, artifact |
| 409 | `IDEMPOTENCY_CONFLICT` | 同一キーでボディ差分 | 既存 payload と digest 不一致 |
| 429 | `RATE_LIMITED` | レート超過 | `Retry-After` 付与 |
| 502 | `AIRFLOW_DOWN` | Airflow 未応答 | Adapter または upstream |
| 500 | `INTERNAL_ERROR` | 予期せぬ例外 | サーバ障害 |

**表現の一貫性**：スタックトレースや機微情報は**返さない**。詳細はサーバログへ。

---

## 7. ページング / ソート / フィルタ
### 7.1 ページング
- **クエリ**：`page`（>=1, 既定1）、`page_size`（10..100, 既定50）  
- **レスポンス**：`{ items:[], page, page_size, total }`  
- **ソート**：`sort=field.direction`（例：`last_checked_at.desc`）

### 7.2 フィルタ（一覧）
- CSV 構文：`tags_any=daily,priority` / `health=healthy,degraded`  
- 入力サニタイズ：`q` は 64文字以内、ワイルドカード注入に注意（`%` や `_` のエスケープ）。

---

## 8. レート制限
- 既定値（ガイドライン、実値は `RateLimit-Quota-DoLayer.md` を参照）  
  - 読み取り：600 rpm / client  
  - 再チェック：120 rpm / client  
  - 一括再チェック：10 rpm / client  
- **超過時**：429 + `Retry-After`。  
- **ヘッダ（任意）**：`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`。

---

## 9. サイズとタイムアウト
- リクエストボディ：**64KB** 目安（`/pdca/recheck*`）  
- レスポンス：**1MB** 目安（一覧はページサイズで抑制）  
- タイムアウト：10s（上流→Airflowは非同期、受理は速やかに）

---

## 10. 可観測性（最低限）
- **メトリクス**：
  - `pdca.api.requests_total{endpoint,outcome}`  
  - `pdca.api.latency_ms{endpoint}`（histogram）  
  - `pdca.api.idempotency_conflicts_total`  
  - `airflow.adapter.requests_total{endpoint,outcome}`
- **ログ（構造化）**：`x_request_id, client_id, endpoint, http_status, latency_ms, request_id?`  
- **トレース**：入口Span + Airflow Adapter/DBへの子Span。

---

## 11. サンプル（curl）
### 11.1 単体再チェック（dry run）
```bash
curl -sS -X POST "$API/pdca/recheck" \
 -H "Authorization: Bearer $JWT" \
 -H "Content-Type: application/json" \
 -H "Idempotency-Key: 01J8TPZ7YJ1E1X4C5N9ZP3M3QJ" \
 -d '{
   "strategies":["strat.meanrev.m1"],
   "window":{"lookback_days":14},
   "reason":"manual",
   "dry_run":true,
   "params":{"recalc_metrics":["sharpe"]}
 }'
```

### 11.2 一括再チェック（実行）
```bash
curl -sS -X POST "$API/pdca/recheck_all" \
 -H "Authorization: Bearer $JWT" \
 -H "Content-Type: application/json" \
 -H "Idempotency-Key: 01J8TPZ7YJ1E1X4C5N9ZP3M3QA" \
 -d '{
   "filter":{"tags_any":["daily"],"health":["unknown"]},
   "batch_size":25,
   "window":{"lookback_days":7},
   "reason":"daily-bulk",
   "dry_run":false
 }'
```

### 11.3 進捗参照
```bash
curl -sS "$API/pdca/recheck/01JABCXYZ-ULID-5678" \
 -H "Authorization: Bearer $JWT"
```

### 11.4 データ一覧（GUI）
```bash
curl -sS "$API/gui/strategies?health=healthy&sort=last_checked_at.desc&page=1&page_size=50" \
 -H "Authorization: Bearer $JWT"
```

---

## 12. バリデーション規約（抜粋）
- `strategies[]`: 1..50, `/^[a-z0-9._-]+$/`  
- `window`: `from<=to`、または `lookback_days`（1..180）との**排他**  
- `reason`: 1..64 chars（英数と`[._-]`中心、和文可）  
- `trace_id`: 1..128 chars（ログ相関用、digestからは除外可）  

---

## 13. 互換性の扱い（変更ポリシー）
- **追加**：既存フィールドは不変。新フィールドは**任意**で追加。  
- **非推奨**：OpenAPI `deprecated: true` + Markdownで告知。  
- **削除**：次メジャー（`/v2`）以降でのみ。少なくとも**90日**前に告知。

---

## 14. 実装者チェックリスト
- [ ] OpenAPI に**同内容**が反映されている  
- [ ] 202 で **`request_id` を必ず返す**  
- [ ] `Idempotency-Key` を検証し **digest 完全一致のみ再利用**  
- [ ] 429 で `Retry-After` を返却  
- [ ] 404/409/5xx の**メッセージ定形**を統一  
- [ ] ログに **`x_request_id` と `request_id`** を残す  
- [ ] 機微情報をログ/エラーに出さない  
- [ ] ページングの `total` を正しく返す  
- [ ] OpenAPI の Example と実装レスポンスが一致

---

## 15. 変更履歴
- **2025-08-24**: 初版（原則、幂等/正規化、エラー、ページング/レート、例、チェックリスト）
