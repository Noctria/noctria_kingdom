# Contract: OrderRequest (v1.1)
**Status:** Stable  
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Do-Layer / Execution Team

## 0. 概要
注文実行の唯一の正準契約。**v1.1 で `idempotency_key` を追加**し、変更系要求の重複処理を安全化。ヘッダの `Idempotency-Key` とボディ `order_request.idempotency_key` は**一致必須**。

## 1. ヘッダ
- `Idempotency-Key: <UUID or ULID>` **(required; MUST equal body.idempotency_key)**
- `Content-Type: application/json`

## 2. ボディ
```json
{
  "order_id": "string (client logical id)",
  "instrument": "USDJPY",
  "side": "BUY|SELL",
  "qty": 0.10,
  "price": null,
  "time_in_force": "IOC|FOK|GTC",
  "tags": ["pdca","recheck"],
  "idempotency_key": "01JABCDXYZ-ULID-1234",
  "requested_at": "2025-08-24T00:00:00Z",
  "risk_constraints": {
    "max_dd": 0.10,
    "max_consecutive_loss": 3,
    "max_spread": 0.002
  }
}
```

## 2.1 型と制約
- `instrument`: 取引可能ペア（例: `USDJPY`, `EURUSD`）。GUI側のバリデーション表に準拠。
- `qty`: ブローカー最小LOT・STEPに整合（例: 0.01 STEP）。
- `price`: 成行は `null`。指値/逆指値なら有値。
- `time_in_force`: `IOC|FOK|GTC`。既定 `IOC`。
- `risk_constraints.max_spread`: 省略時は Do-Layer 既定を適用。

## 3. 幂等（Idempotency）
- **一致必須**: `header.Idempotency-Key == body.idempotency_key`
- **同一キー再送時の応答**:
  - ボディ完全一致 → `200 OK`（再処理なし、前回結果を返す）
  - ボディ差分あり → `409 Conflict`
- **保存**: Do-Layer は `idempo_ledger` に `idempotency_key` と `request_digest`・`result_digest` を保存（TTL付き）。

## 4. レスポンス（要点）
- `201 Created`: 新規受理、執行キュー投入
- `200 OK`: 幂等成立（再送）
- `409 Conflict`: 同一キーでボディ差分
- `422 Unprocessable Entity`: バリデーション不一致
- `429 Too Many Requests`: レート制限

## 5. 監査・可観測性
- `obs_infer_calls` に trace_id / model_id / latency
- `idempo_ledger` に幂等キー結果
- 失敗時は `reason_code` と `retry_after`（必要時）

## 6. 変更履歴
- **v1.1 (2025-08-24)**: `idempotency_key` を追加し、ヘッダ一致を必須化。`409` ルールを明文化。
- v1.0: 初版
