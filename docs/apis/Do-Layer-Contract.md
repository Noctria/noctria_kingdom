# Do-Layer API — Order Execution (v1.1 aligned)
**Last Updated:** 2025-08-24 (JST)

## 0. 概要
Do-Layer が提供する注文実行 API。`OrderRequest v1.1` に準拠し、`Idempotency-Key` を必須とする。

## 1. エンドポイント
- **POST** `/do/order`

## 2. ヘッダ
- `Idempotency-Key` (required; MUST equal body.idempotency_key)  
- `Content-Type: application/json`

## 3. リクエスト
- Body: [`OrderRequest v1.1`](../architecture/contracts/OrderRequest.md)

### サンプル
```json
{
  "order_id": "ord-12345",
  "instrument": "USDJPY",
  "side": "BUY",
  "qty": 0.10,
  "price": null,
  "time_in_force": "IOC",
  "tags": ["pdca","recheck"],
  "idempotency_key": "01JABCXYZ-ULID-5678",
  "requested_at": "2025-08-24T00:00:00Z",
  "risk_constraints": {
    "max_dd": 0.1,
    "max_consecutive_loss": 3
  }
}
```

## 4. レスポンス
- `201 Created` — 新規受理（執行キュー登録）  
- `200 OK` — 幂等成立（同一キー・同一ボディの再送）  
- `409 Conflict` — 同一キー・ボディ差分  
- `422 Unprocessable Entity` — バリデーションエラー  
- `429 Too Many Requests` — レート制限

### エラーレスポンス例
```json
{
  "error": "IDEMPOTENCY_CONFLICT",
  "message": "body differs from previous request with same key",
  "idempotency_key": "01JABCXYZ-ULID-5678"
}
```

## 5. 可観測性
- `idempo_ledger` に要求/結果ダイジェスト、TTL を記録  
- `obs_infer_calls` に trace_id / latency / model_id を記録  

## 6. Notes
- Do-Layer 内の order_router は、REST 経由と内部呼び出しの双方で同一バリデーションを適用すること。  
- 幂等キー衝突の頻度はメトリクスにカウントし、HUD に「API健全性カード」として表示する。
