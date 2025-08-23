# ⚔️ Contract: OrderRequest v1.1

> **目的**: 決定された取引アクションを **実執行可能な形** に落とし込む最終契約。  
> **利用層**: DecisionEngine → Do層（order_execution, broker adapter）

---

## バージョン
- **v1.0**: 初版（基本フィールドのみ）
- **v1.1**: `idempotency_key` を追加（後方互換）

---

## JSON Schema（v1.1）

```json
{
  "title": "OrderRequest",
  "version": "1.1",
  "type": "object",
  "required": ["symbol", "side", "qty", "trace_id", "idempotency_key"],
  "properties": {
    "symbol": {
      "type": "string",
      "description": "通貨ペア（例: USDJPY）"
    },
    "side": {
      "type": "string",
      "enum": ["BUY", "SELL", "FLAT"],
      "description": "売買方向またはノーポジ"
    },
    "qty": {
      "type": "number",
      "description": "発注数量（units, 正規化済み）"
    },
    "price": {
      "type": ["number", "null"],
      "description": "指値注文の場合の価格（null なら成行）"
    },
    "order_type": {
      "type": "string",
      "enum": ["MARKET", "LIMIT", "STOP"],
      "default": "MARKET"
    },
    "time_in_force": {
      "type": "string",
      "enum": ["GTC", "IOC", "FOK"],
      "default": "GTC"
    },
    "trace_id": {
      "type": "string",
      "description": "Plan→AI→Decision→Do を貫通する相関ID"
    },
    "decision_id": {
      "type": ["string", "null"],
      "description": "DecisionRecordに紐づくID（将来用）"
    },
    "idempotency_key": {
      "type": "string",
      "description": "冪等制御キー: `symbol|side|qty|ts_floor_minute|trace_id` を HMAC-SHA256（32〜64 hex）"
    },
    "meta": {
      "type": "object",
      "description": "任意メタデータ（strategy, policy 等）"
    }
  }
}
```

---

## サンプル（v1.1）

```json
{
  "symbol": "USDJPY",
  "side": "BUY",
  "qty": 10000,
  "price": null,
  "order_type": "MARKET",
  "time_in_force": "GTC",
  "trace_id": "trace-abc-123",
  "decision_id": "dec-xyz-999",
  "idempotency_key": "7f9e1a23c4b5d67890ef...",
  "meta": {
    "strategy": "Aurus",
    "reason": "breakout confirmed"
  }
}
```

---

## 備考
- `idempotency_key` は **broker送信・Outbox一意制御・exec_result照合** すべてに利用。
- 生成方法は `make_idem_key(symbol, side, qty, trace_id, ts_floor_minute)` に準拠。
- v1.0 クライアントは `idempotency_key` 未対応でも許容されるが、Do層で付与される。

## Idempotency & Outbox (v1.1)

**目的**: 同一発注の重複送信を防ぎ、再送でも外部ブローカ送信が1回に保たれること。

### キー定義
- `idempotency_key`（**必須推奨**）: 同一性を表す32〜64hex。
- 推奨生成式（分丸め & 量丸め6桁）  
  `base = "symbol|side|qty_rounded6|ts_floor_minute|trace_id"` → `HMAC-SHA256(base, SECRET)`

### 例（Python）
```python
import hmac, hashlib, os
SECRET = os.getenv("NOCTRIA_IDEMPOTENCY_SECRET", "dev-secret")
def make_idem_key(symbol, side, qty, trace_id, ts_iso):
    ts_floor_min = ts_iso[:16] + "Z"           # "YYYY-MM-DDTHH:MMZ"
    qty_s = f"{float(qty):.6f}"
    base = f"{symbol}|{side}|{qty_s}|{ts_floor_min}|{trace_id}"
    return hmac.new(SECRET.encode(), base.encode(), hashlib.sha256).hexdigest()[:32]
