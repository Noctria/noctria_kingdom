# Security: Do-Layer 認証・認可ポリシー
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Platform / Security

---

## 0. 目的
`/do/order` を含む Do 層 API の **AuthN（認証）/AuthZ（認可）** を標準化し、誤送・権限過剰・キー漏洩リスクを最小化する。

---

## 1. トークン形式
- **推奨:** JWT (RS256)  
  - `iss`（発行者）: `noctria.auth`  
  - `aud`（受信者）: `do-layer`  
  - `sub`（主体）: client_id（サービス名）  
  - `exp`（有効期限）: ≤ 15m（短命）  
  - `scope`（権限）: 例 `order:submit`  
- **代替（小規模・試験）:** Static API Key（HMAC 署名付与と併用）

### 1.1 署名キー
- 検証: 公開鍵（JWKS エンドポイント or 環境変数）  
- ローテーション: 90日、旧鍵は30日併用

---

## 2. 認可（スコープ/ロール）
- `order:submit` → `/do/order` POST  
- `order:read` → `GET /do/order/:id`（将来拡張）  
- `ops:purge` → 内部運用 API（非公開）
- 原則 **最小権限**、サービス単位で client_id を分離

---

## 3. リクエスト検証フロー
1) `Authorization: Bearer <JWT>` を抽出  
2) ヘッダ/署名/`exp`/`aud`/`iss` を検証  
3) `scope` に `order:submit` を含むか確認  
4) `Idempotency-Key == body.idempotency_key` を検証（契約整合）  
5) Rate Limit/Quota チェック（別紙参照）

不一致時の応答:
- 401: 無効トークン/期限切れ
- 403: 権限不足（scope 不足）

---

## 4. クライアント識別と監査
- ログキー: `client_id(sub)`, `scope`, `trace_id`, `idempotency_key(hash)`  
- メトリクス: `auth.denied_total{reason}`, `auth.accepted_total`

---

## 5. 構成（.env / 証明書）
```dotenv
DO_JWT_AUDIENCE=do-layer
DO_JWT_ISSUER=noctria.auth
DO_JWKS_URL=https://auth.noctria.local/.well-known/jwks.json
# or RS256 公開鍵を直接
DO_JWT_PUBLIC_KEY_BASE64=...
```

---

## 6. テストベクタ（例）
- 期限切れ `exp`、`aud` 不一致、`scope` 欠落、署名不正の4種をE2Eに含める

---

## 7. 変更履歴
- **2025-08-24**: 初版
