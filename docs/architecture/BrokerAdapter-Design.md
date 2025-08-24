# BrokerAdapter — 詳細設計（IF差分 / 署名 / 時刻同期 / レート / エラー語彙）
**Status:** Stable Candidate  
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Do-Layer / Platform

関連:
- `docs/architecture/contracts/OrderRequest.md`（v1.1: `idempotency_key`）  
- `docs/architecture/Outbox-Worker-Protocol.md`（Outbox 送信と再試行）  
- `migrations/20250824_add_idempo_ledger.sql`（`idempo_ledger`）  
- `docs/security/AuthN-AuthZ-DoLayer.md`（Secrets/監査/認可）  
- `docs/observability/DoLayer-Metrics.md`（メトリクス語彙；別ファイル）

---

## 0. 目的
外部ブローカーへの**実行IF差分**をアダプタで吸収し、**安全に一意送信**する。  
- **冪等**：`OrderRequest.idempotency_key` を貫通、重複送信を抑止  
- **署名**：ブローカー毎の署名/認証（HMAC/JWT/Key+Nonce）を統一抽象化  
- **時刻同期**：`ts` と `nonce` を正しく生成・検証（clock drift 管理）  
- **レート/再試行**：ブローカー別の上限/バックオフに準拠  
- **エラー語彙**：異種のエラーを**正準 reason_code**へマップ

---

## 1. サマリ方針
- **Adapter Interface = 最小核**（send/cancel/status/positions/heartbeat）。  
- **Broker Profile**（YAML/ENV）で差分をデータ駆動化（署名/エンドポイント/レートなど）。  
- Outbox Worker が **Adapter を呼ぶだけ**で各社仕様を満たす。

---

## 2. 共通インタフェース
```python
class BrokerAdapter(Protocol):
    name: str
    profile: BrokerProfile

    def send_order(self, req: OrderRequest) -> SendResult: ...
    def cancel_order(self, broker_order_id: str, *, symbol: str | None = None) -> CancelResult: ...
    def get_order_status(self, broker_order_id: str) -> OrderStatus: ...
    def get_positions(self) -> list[Position]: ...
    def heartbeat(self) -> Heartbeat: ...
```

### 2.1 型（要点）
- `OrderRequest` … `symbol | intent(BUY/SELL) | qty | limit_price? | sl_tp? | trace_id? | idempotency_key`  
- `SendResult` … `ok, broker_order_id?, filled_qty?, avg_price?, reason_code?, http_status?`  
- `OrderStatus` … `status(New/PartiallyFilled/Filled/Cancelled/Rejected), last_update_at, reason?`  
- **全てに** `idempotency_key` を通す（可能な限り）

---

## 3. 正規化・冪等・署名
### 3.1 正規化
- Outbox 保存時に **Canonical JSON** と `request_digest` を計算（ガイド参照）。  
- Adapter 送信時は**同一正規化**を使用（ログ/監査のハッシュ一致）。

### 3.2 冪等
- **ヘッダ/フィールド**で `Idempotency-Key` を送る（ブローカーが支持する場合）。  
- 非対応ブローカーは **Adapter 内でリプレイ検知**（`idempo_ledger` と `result_digest`）。  
- **409 already processed** を**成功準拠**として扱う（詳細は Outbox に従う）。

### 3.3 署名（パターン）
- **HMAC-SHA256**：`sign = HMAC(secret, method|path|query|body|ts|nonce)`  
- **JWT（HS/RS）**：`Authorization: Bearer <jwt(payload: ts, nonce, key_id)>`  
- **APIKey + Nonce**：`X-API-Key, X-Nonce, X-Timestamp, X-Signature`  
- **Query Presign**（一部 GET）：`?ts=...&nonce=...&sig=...`

> ボディ署名は **正規化JSON** を用いる（空白差の影響排除）。

---

## 4. 時刻同期（Clock）
- 許容ドリフト：**±2s**（既定；厳格ブローカーは ±500ms）。  
- **同期手段**：  
  1) ブローカー `GET /time` があれば優先（往復遅延/2 で補正）  
  2) NTP（`pool.ntp.org` 等／K8s ノード同期）  
- **監視**：`broker.clock_drift_ms{broker}` を収集、閾値超で WARN。  
- **送信ヘッダ**：`X-Timestamp: epoch_ms`（profile で秒/ミリ選択）

---

## 5. レート制御・再試行
### 5.1 レート
- **クライアント側トークンバケット**（Burst/Rate は profile）。  
- 429/`Retry-After` を尊重（秒/ミリ両対応）。  
- メトリクス: `broker.ratelimited_total{broker}`。

### 5.2 再試行
- 対象：**ネットワーク/5xx/429**。  
- バックオフ：指数 + ジッタ（例：`base=0.5s`, 最大 8 回）。  
- 非再試行：**400/422/403/401**（設定不備や仕様違反）。  
- 409 “processed” は成功扱い（冪等合意時）。

---

## 6. エラー語彙（正準 reason_code）
| カテゴリ | reason_code | 例（ブローカー生値） | API応答 |
|---|---|---|---|
| 認証/権限 | `BROKER_UNAUTHORIZED` | 401/403, `INVALID_APIKEY` | 502/500 相当（内部遮断） |
| 入力不正 | `BROKER_BAD_REQUEST` | 400/422, `SYMBOL_INVALID`, `INSUFFICIENT_MARGIN` | 400 |
| レート超過 | `BROKER_RATE_LIMITED` | 429, `TOO_MANY_REQUESTS` | 502/429（状況に応じ） |
| 一時障害 | `BROKER_5XX` | 500/503 | 502 |
| タイムアウト | `BROKER_TIMEOUT` | client timeout | 502 |
| 冪等既処理 | `BROKER_ALREADY_PROCESSED` | 409, `DUPLICATE_ORDER` | 200/202 等価 |
| 不明 | `BROKER_UNKNOWN` | parse error | 500 |

> **Do-Layer の外向け**エラーは `Do-Layer-OrderAPI-Spec` に定義した語彙へ再マップ。

---

## 7. Broker Profiles（例）  
> 実社名は伏せ、**3タイプ**で差分を示す。実装時は `config/broker/*.yaml` で定義。

### 7.1 `NoctriaPaper`（社内シミュレータ / REST）
- base: `http://paper-broker:9000`  
- auth: `X-API-Key`, `X-Timestamp`, `X-Nonce`, `X-Signature(HMAC)`  
- idempotency: **ヘッダ対応**（`Idempotency-Key` 必須）  
- rate: `rate=20 rps`, `burst=40`  
- time: `/v1/time` あり（ms）  
- **エンドポイント**  
  - `POST /v1/orders` （発注）  
  - `GET  /v1/orders/{id}`（状態）  
  - `DELETE /v1/orders/{id}`（キャンセル）  
- **発注ボディ（例）**
```json
{
  "symbol":"USDJPY",
  "side":"BUY",
  "qty":10000,
  "type":"limit",
  "limit_price":145.001,
  "idempotency_key":"01JABCXYZ-ULID-5678",
  "client_tag":"DoLayer",
  "ts": 1724463610000
}
```
- **署名文字列**：`"POST|/v1/orders||<canonical_body>|1724463610000|<nonce>"`

### 7.2 `AlphaTradeRESTv2`（外部社 / REST+JWT）
- base: `https://api.alphatrade.example.com`  
- auth: `Authorization: Bearer <JWT(iss,sub,ts,nonce)>`（RS256）  
- idempotency: **未対応** → Adapter が `idempo_ledger` で重複吸収  
- rate: `rate=5 rps`, `burst=10`、429 に `Retry-After`（秒）  
- time: `/v2/server-time`（秒）  
- **発注**：`POST /v2/orders`、応答 201 で `order_id`。  
- **エラー生値**：`{"code":"SYMBOL_INVALID"}`, `{"code":"ALREADY_EXISTS"}` 等 → マップ

### 7.3 `OmegaFIX44`（外部社 / FIX 4.4 経由）
- 送信は **FIX セッション**（SenderCompID/TargetCompID）。  
- Adapter は **FIX-GW**（内部 Sidecar）へ gRPC 送信 → 変換して 35=D（NewOrderSingle）。  
- **冪等**：`ClOrdID = idempotency_key`（**必須**）  
- **状態**：35=8（ExecutionReport）で `OrdStatus` → 内部 OrderStatus へ変換  
- **キャンセル**：35=F（OrderCancelRequest）  
- **レート**：FIX-GW でレート制御（セッション単位）。  
- **時刻**：GW ノードの NTP を信頼（サーバ `/time` は無い）。

---

## 8. セキュリティ
- Secrets は **KMS/Secrets Manager** または **K8s Secrets** から注入。  
- 署名/トークン/鍵は**ログ出力禁止**、監査は `kid` 等の**メタのみ**。  
- TLS 設定は profile で `verify=true/ca_bundle=/etc/ssl/custom.pem` を切替。  
- キー ローテ：`kid` を用意し**二重署名期間**を許容（古い鍵で失敗→新鍵リトライ）。

---

## 9. 可観測性
- **Metrics**（Prometheus）
  - `broker.http.requests_total{broker,endpoint,code}`  
  - `broker.http.latency_ms{broker,endpoint}`（histogram）  
  - `broker.retry_total{broker,reason}`  
  - `broker.clock_drift_ms{broker}`（gauge）  
- **Logs（構造化）**
  - `broker, endpoint, http_status, reason_code, latency_ms, idempotency_key, broker_order_id?`  
- **Tracing**
  - span: `broker.send_order` / `broker.cancel` / `broker.status`  
  - attributes: `broker, endpoint, http_status, retry_count`

---

## 10. コンフィグ（ENV / YAML）
| Key | 既定 | 説明 |
|---|---|---|
| `BROKER_PROFILE` | `NoctriaPaper` | 使用プロファイル名 |
| `BROKER_BASE_URL` | by profile | REST base |
| `BROKER_AUTH_MODE` | `hmac|jwt|apikey|fix` | 署名方式 |
| `BROKER_API_KEY` | - | 任意 |
| `BROKER_API_SECRET` | - | 任意（HMAC） |
| `BROKER_JWT_KID` | - | JWT 署名 kid |
| `BROKER_RATE_RPS` | by profile | レート上限 |
| `BROKER_RATE_BURST` | by profile | バースト |
| `BROKER_TIMEOUT_SEC` | `5` | HTTP タイムアウト |
| `BROKER_RETRY_MAX` | `8` | 再試行上限 |
| `BROKER_TLS_VERIFY` | `true` | 証明書検証 |
| `BROKER_TIME_ENDPOINT` | `"/time"` | サーバ時間 API（無ければ空） |
| `BROKER_TIMESTAMP_UNIT` | `ms|s` | ts 単位 |
| `BROKER_IDEM_HEADER` | `Idempotency-Key` | ヘッダ名（空=未対応） |

---

## 11. 擬似コード（送信とマッピング）
```python
def send_order(self, req: OrderRequest) -> SendResult:
    # 1) 署名素材の準備
    ts = now_epoch(self.profile.ts_unit)
    nonce = ulid()[:26]
    body = canonical_json({
        "symbol": req.symbol,
        "side": req.intent,
        "qty": req.qty,
        **({"limit_price": req.limit_price} if req.limit_price else {}),
        "idempotency_key": req.idempotency_key if self.profile.idem_supported else None,
        "client_tag": "DoLayer",
        "ts": ts
    })
    # 2) ヘッダ
    headers = self._auth_headers(method="POST", path="/v1/orders", body=body, ts=ts, nonce=nonce)
    if self.profile.idem_header:
        headers[self.profile.idem_header] = req.idempotency_key
    # 3) レート取得
    self.rate_limiter.acquire()
    # 4) 送信 + 再試行
    for attempt in range(self.retry_max):
        try:
            r = httpx.post(self.base+"/v1/orders", content=body, headers=headers, timeout=self.timeout)
            if r.status_code in (200,201,202):  # 成功
                data = r.json()
                return SendResult(ok=True, broker_order_id=data.get("order_id") or data.get("broker_order_id"))
            if r.status_code == 409 and self.profile.idem_supported:
                return SendResult(ok=True, reason_code="BROKER_ALREADY_PROCESSED")
            if r.status_code in (401,403,400,422):
                return SendResult(ok=False, reason_code=map_code(r), http_status=r.status_code)
            if r.status_code in (429,500,502,503):
                sleep_jittered(attempt)
                continue
            return SendResult(ok=False, reason_code="BROKER_UNKNOWN", http_status=r.status_code)
        except httpx.TimeoutException:
            sleep_jittered(attempt)
        except httpx.RequestError:
            sleep_jittered(attempt)
    return SendResult(ok=False, reason_code="BROKER_TIMEOUT")
```

---

## 12. テスト計画
- **Unit**：署名生成（ボディ差替えでハッシュ不一致を検知）  
- **Contract（モック）**：各プロファイルの**擬似サーバ**で 2xx/4xx/5xx/429/409 を網羅  
- **Idempotency**：同一 `idempotency_key` で**二重送信→1回成功**（409 を成功扱い）  
- **Rate**：限界超で `broker.ratelimited_total` が増える／待機で収束  
- **Clock**：±3s ドリフトで署名 NG → `/time` 取得後 OK  
- **Chaos**：DNS/ネットワーク切断 → 再試行で回復、Outbox は再キュー

---

## 13. ロールアウト
1. **Canary**：`NoctriaPaper` → 小規模実運転（Outbox Lag/Sent率監視）  
2. **外部1社**：`AlphaTradeRESTv2` を FeatureFlag で 5%→50%→100%  
3. **FIX系**：`OmegaFIX44` は別 Pod として独立ロールアウト  
4. **フェイルバック**：グローバルスイッチで **Adapter=DryRun**（発注停止）可能

---

## 14. 変更履歴
- **2025-08-24**: 初版（IF・署名・時刻同期・レート・エラー・Profiles・擬似コード・試験）
