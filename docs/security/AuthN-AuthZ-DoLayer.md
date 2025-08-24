# Do-Layer / PDCA — AuthN・AuthZ・Audit 設計詳細
**Status:** Stable Candidate  
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Platform / Security

関連:
- `docs/apis/openapi/pdca-api.yaml`（唯一の機械可読契約）
- `docs/apis/PDCA-API-Design-Guidelines.md`（横断ガイド）
- `docs/integration/Airflow-RestAdapter-Design.md`（上流連携の失敗時の扱い）
- `docs/architecture/schema/PDCA-MetaSchema.md`（`pdca_requests` ほか）
- `docs/platform/RateLimit-Quota-DoLayer.md`（割当と鍵の定義）

---

## 0. 目的
PDCA/GUI API の **認証 (AuthN)**、**認可 (AuthZ)**、および **監査ログ (Audit)** を統一的に定義する。  
- JWT (RS256) 検証の手順  
- スコープとエンドポイントの対応表  
- Idempotency と監査の相関  
- ログ項目・マスキング・保持ポリシー

---

## 1. トラストモデル & トランスポート
- **TLS 必須**: 外部公開は HTTPS/TLS1.2+。`HSTS(max-age=31536000)` を推奨。
- **mTLS（任意）**: サービス間（API → Airflow Adapter）は内部ネットワークで mTLS を許す設計に対応。
- **CORS**: GUI ドメインのみ許可（`Origin` allowlist、`Authorization` ヘッダ expose）。

---

## 2. 認証 (AuthN) — JWT (RS256)
### 2.1 受入要件（JOSE ヘッダ/クレーム）
- JOSE ヘッダ: `alg=RS256`, `typ=JWT`, **`kid` 必須**  
- クレーム（必須）:
  - `iss`: `noctria.auth`
  - `aud`: `pdca`（書き系）または `pdca.gui`（読み系）
  - `sub`: クライアントID（人 or サービスアカウント）
  - `exp`: 有効期限（<= 1h 推奨）
  - `iat` / `nbf`（任意だが推奨）
  - `scope`: 文字列（空白区切り） or 配列（後述の正規化で等価扱い）
- クレーム（任意/採用可）:
  - `tenant_id`: テナント境界の強制フィルタに利用
  - `jti`: リプレイ検知（書き系で使用可）
  - `azp` / `client_id`: 発行者側互換のため保持可

### 2.2 検証手順（順序）
1. **パース**（サイズ上限 8KB、ヘッダの `kid` を取得）  
2. **JWKS 取得/キャッシュ**（`kid` に一致する公開鍵を 10 分キャッシュ, 24h TTL 上限）  
3. **署名検証**（RS256）  
4. **クレーム検証**  
   - `iss == "noctria.auth"`  
   - `aud ∈ {"pdca","pdca.gui"}`（エンドポイントにより許容集合を切替）  
   - `exp > now + skew`、`nbf <= now + skew`、`iat > now - max_lookback`  
     - **clock skew** は ±120 秒許容  
5. **スコープ正規化**（空白区切り文字列→配列、重複除去、小文字化）  
6. **テナント境界**（`tenant_id` があれば DB クエリで強制 AND）

> **失敗時の応答**: 401 `UNAUTHORIZED`（`WWW-Authenticate: Bearer error="invalid_token"` を付与）

### 2.3 擬似コード（検証）
```python
def verify_jwt(jwt_token: str, required_aud: set[str]) -> Claims:
    header = parse_header(jwt_token)
    key = jwks_cache.get(header.kid) or fetch_and_cache_jwks(header.kid)
    claims = jose_jwt.decode(jwt_token, key, algorithms=["RS256"], audience=list(required_aud), issuer="noctria.auth",
                             options={"leeway": 120})
    scopes = normalize_scopes(claims.get("scope"))
    return Claims(
        sub=claims["sub"], aud=claims["aud"], tenant_id=claims.get("tenant_id"),
        scopes=scopes, jti=claims.get("jti"), kid=header.kid, raw=claims
    )
```

---

## 3. 認可 (AuthZ) — スコープとエンドポイント
### 3.1 スコープ一覧
- `pdca:read` — 一覧/詳細/成果物URL取得  
- `pdca:download` — 署名付きURLの発行（ダウンロード操作）  
- `pdca:recheck` — 単体再チェックの受理  
- `pdca:recheck_all` — 一括再チェックの受理（より強い権限）

### 3.2 エンドポイント対応表
| Endpoint | Method | 必須 aud | 必須 scope |
|---|---|---:|---|
| `/gui/strategies` | GET | `pdca.gui` | `pdca:read` |
| `/gui/strategies/:id` | GET | `pdca.gui` | `pdca:read` |
| `/gui/strategies/:id/results` | GET | `pdca.gui` | `pdca:read` |
| `/gui/requests/:request_id` | GET | `pdca.gui` | `pdca:read` |
| `/gui/artifacts/:artifact_id/url` | GET | `pdca.gui` | `pdca:download` |
| `/pdca/recheck` | POST | `pdca` | `pdca:recheck` |
| `/pdca/recheck_all` | POST | `pdca` | `pdca:recheck_all` |
| `/pdca/recheck/:request_id` | GET | `pdca.gui` | `pdca:read` |

> **スコープ不足**は 403 `FORBIDDEN`。監査には **不足スコープ**を記録。

---

## 4. Idempotency / JTI / 監査の相関
- 書き系（`/pdca/recheck*`）は **`Idempotency-Key`（必須）** を第一の冪等機構に利用。  
- `jti`（任意）を**二重送信検知**の補助として採用可（TTL＝`exp` まで）。  
- 監査ログには **`idempotency_key` と `request_digest`** を記録するが、**ボディ実体は保存しない**（機微保護）。

---

## 5. 監査ログ (Audit) — スキーマ
### 5.1 目的
- **誰が（client_id/tenant）いつ（ts）何を（endpoint/params）要求し**  
- **結果はどうだったか（http_status/error/reason）** を非否認性のある形で保持。

### 5.2 形式
- **JSON Lines (UTF-8)**、1 行 1 イベント  
- **UTC RFC3339** タイムスタンプ  
- **マスキング/ハッシュ**済み（下記参照）

### 5.3 推奨フィールド
```json
{
  "ts": "2025-08-24T03:34:56Z",
  "x_request_id": "01JB4A...X",
  "client_id": "ops-ui",
  "tenant_id": "tnt-001",
  "aud": "pdca.gui",
  "scopes": ["pdca:read"],
  "jwt": { "kid": "K1", "iss": "noctria.auth" },

  "method": "POST",
  "path": "/pdca/recheck",
  "route": "/pdca/recheck",
  "query": { "page": "1" },

  "idempotency_key": "01J8TPZ7YJ1E...",
  "request_digest": "sha256:2f8a...",
  "request_id": "01JABCXYZ-ULID-5678",   // 受理後に付与
  "dag_run_id": "manual__2025-08-24T03:35:00+00:00__b1", // あれば

  "http_status": 202,
  "error": null,                  // 例: "UNAUTHORIZED" / "RATE_LIMITED"
  "reason_code": null,            // 例: "AIRFLOW_TIMEOUT"（Adapter マップ）
  "rows": 37,                     // レスポンス中の items 件数（GET系）
  "latency_ms": 128,

  "remote_addr_hash": "sha256:abcd...",   // IP はハッシュ化
  "user_agent": "Mozilla/5.0 (…)",

  "notes": null
}
```

### 5.4 マスキング/除外ルール
- **絶対に保存しない**: `Authorization` ヘッダ、完全なリクエストボディ（/pdca/recheck* は**ダイジェストのみ**）  
- **マスク**: JWT の `kid/iss/aud` 以外のクレームは記録しない（必要時は `sub` のみ）  
- **ハッシュ**: `remote_addr` は SHA-256（ソルト有り）で不可逆化  
- **サイズ制限**: `query` は 1KB まで、超過時は省略（`truncated: true` をメモ）

### 5.5 保持ポリシー
- 標準: **90 日**（本番）  
- 高詳細（DEBUG/TRACE 相当）: **7 日**  
- すべて**暗号化 at-rest**（ボリューム暗号 or KMS）

---

## 6. レート制限 / クォータ（Auth と連動）
- **鍵**: `client_id (+ tenant_id)` を基本。  
- **スコープ別の上限**（例）:
  - `pdca:read`: 600 rpm  
  - `pdca:recheck`: 120 rpm  
  - `pdca:recheck_all`: 10 rpm  
- 429 時は `Retry-After` を返却。監査に `rate_bucket_remaining` を付加可能。

---

## 7. セキュリティヘッダ/レスポンスポリシー
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: default-src 'none'`（API応答は JSON のみ）
- `Cache-Control: no-store`（認証関連応答）

---

## 8. 責務分担（AuthN/AuthZ/Audit）
| 層 | 責務 |
|---|---|
| **Edge/Ingress** | TLS 終端、ベーシックな WAF ルール、最大ボディサイズ制限 |
| **API Gateway（任意）** | 事前 JWT 検査/レート（粗粒度） |
| **PDCA API** | 本検証（aud/scope/claims）、細粒度レート、Idempotency、監査、Adapter 連携 |
| **Airflow Adapter** | Secrets 保護、上流のエラー→`reason_code` マッピング、最少権限 |

---

## 9. 異常系の取り扱い（統一）
| 事象 | 応答 | 監査の `error/reason_code` |
|---|---|---|
| JWT 署名不正/期限切れ | 401 `UNAUTHORIZED` | `UNAUTHORIZED` |
| aud 不一致/スコープ不足 | 403 `FORBIDDEN` | `FORBIDDEN` |
| Idempotency 差分 | 409 `IDEMPOTENCY_CONFLICT` | `IDEMPOTENCY_CONFLICT` |
| レート超過 | 429 `RATE_LIMITED` | `RATE_LIMITED` |
| Airflow 未応答 | 502 `AIRFLOW_DOWN` | `AIRFLOW_DOWN` |
| 内部例外 | 500 `INTERNAL_ERROR` | `INTERNAL_ERROR` |

> **メッセージ**は英語の短文、内部詳細はログのみ。

---

## 10. 実装チェックリスト
- [ ] `Authorization` ヘッダの有無を検査、JWT をパース  
- [ ] JWKS キャッシュ + `kid` で公開鍵ローテに追従  
- [ ] `iss`/`aud`/`exp`/`nbf`/`iat` の検証（±120s skew）  
- [ ] スコープ正規化（空白・配列両対応）  
- [ ] エンドポイント別のスコープ検査  
- [ ] `/pdca/recheck*` は `Idempotency-Key` 必須、**正規化ダイジェスト**で一致判定  
- [ ] 監査ログに **`idempotency_key`/`request_digest`/`request_id`** を記録（ボディは保存しない）  
- [ ] 429 応答に `Retry-After`（秒）  
- [ ] ログに機微情報を含めない（JWT 本文/ボディ/トークン）  
- [ ] 失敗応答は **OpenAPI の Error スキーマ**に一致

---

## 11. テスト計画（Security/E2E 抜粋）
- **T-201**: 署名OK + 正常スコープ → 200/202  
- **T-202**: `aud` 不一致 → 403  
- **T-203**: `exp` 経過/`nbf` 未来 → 401  
- **T-204**: `scope` 不足 → 403  
- **T-205**: `Idempotency-Key` 欠落 → 400  
- **T-206**: 同一キー+同一ボディ → 202 （同 `request_id`）  
- **T-207**: 同一キー+差分ボディ → 409  
- **T-208**: レート超過 → 429 + `Retry-After`  
- **T-209**: JWKS ローテ（`kid` 切替）中も検証継続  
- **T-210**: 監査出力のマスク/ハッシュが有効（leak なし）

---

## 12. 付録 — スコープ正規化
```python
def normalize_scopes(scope) -> list[str]:
    if scope is None: return []
    if isinstance(scope, list):
        items = scope
    else:
        items = str(scope).split()
    return sorted(set(s.strip().lower() for s in items if s.strip()))
```

---

## 13. 変更履歴
- **2025-08-24**: 初版（JWT検証手順、スコープ表、Idempotency連携、Auditフィールド、異常時の規約、チェックリスト）
