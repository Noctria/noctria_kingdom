# Contract: ExecResult (v1.0)
**Status:** Stable Candidate  
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Do-Layer / Execution Team

---

## 0. 目的
注文実行結果の**正準スキーマ**。  
`/do/order` のレスポンスおよび `idempo_ledger.result_digest` 生成の基礎とする。

---

## 1. スキーマ（例）
```json
{
  "status": "ok",
  "order_id": "ord-20250824-0001",
  "instrument": "USDJPY",
  "side": "BUY",
  "requested_at": "2025-08-24T00:00:00Z",
  "completed_at": "2025-08-24T00:00:00Z",
  "trace_id": "trace-abc",
  "idempotency_key": "01JABCXYZ-ULID-5678",
  "fills": [
    {"px": 146.123, "qty": 0.06, "ts": "2025-08-24T00:00:00Z"},
    {"px": 146.129, "qty": 0.04, "ts": "2025-08-24T00:00:00Z"}
  ],
  "avg_price": 146.1252,
  "executed_qty": 0.10,
  "cost": 14612.52,
  "slippage": 0.0003,
  "broker": {
    "name": "paper",
    "order_ref": "bk-7890"
  },
  "latency_ms": {
    "queue": 3,
    "broker_rtt": 22,
    "total": 30
  },
  "reason_code": null,
  "warnings": []
}
```

---

## 2. フィールド定義
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `status` | `"ok" \| "error"` | ✓ | 成功/失敗 |
| `order_id` | string | ✓ | クライアント論理ID（要求継承） |
| `instrument` | string | ✓ | 通貨ペア等 |
| `side` | `"BUY" \| "SELL"` | ✓ | 売買方向 |
| `requested_at` | RFC3339 | ✓ | 要求受領時刻（UTC） |
| `completed_at` | RFC3339 | ✓ | 処理完了時刻（UTC） |
| `trace_id` | string | ✓ | トレースID |
| `idempotency_key` | string | 推奨 | 幂等キー（返せる場合は返す） |
| `fills[]` | array\<Fill\> | ✓(部分約定でも空でない) | 約定明細 |
| `avg_price` | number | 任意 | 加重平均約定価格 |
| `executed_qty` | number | ✓ | 実行数量（0 可。失敗時0） |
| `cost` | number | 任意 | 取引コスト（通貨換算） |
| `slippage` | number | 任意 | 期待→実行の差（割合/abs、実装選択） |
| `broker` | object | ✓ | ブローカー情報 |
| `latency_ms` | object | ✓ | レイテンシ（合計含む） |
| `reason_code` | string\|null | 任意 | 失敗/注意のコード |
| `warnings[]` | string[] | 任意 | 注意事項 |

### 2.1 Fill
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `px` | number | ✓ | 約定価格 |
| `qty` | number | ✓ | 約定数量 |
| `ts` | RFC3339 | ✓ | 約定時刻（UTC） |

### 2.2 broker
```json
{ "name": "paper|real_broker_x", "order_ref": "opaque-id" }
```

### 2.3 latency_ms
```json
{ "queue": 0, "broker_rtt": 22, "total": 30 }
```

---

## 3. 失敗時の例
```json
{
  "status": "error",
  "order_id": "ord-20250824-0002",
  "instrument": "USDJPY",
  "side": "BUY",
  "requested_at": "2025-08-24T00:00:01Z",
  "completed_at": "2025-08-24T00:00:01Z",
  "trace_id": "trace-def",
  "idempotency_key": "01JABCXYZ-ULID-5678",
  "fills": [],
  "executed_qty": 0.0,
  "broker": { "name": "paper", "order_ref": null },
  "latency_ms": { "queue": 1, "broker_rtt": 2500, "total": 2505 },
  "reason_code": "BROKER_TIMEOUT",
  "warnings": ["partial system degradation"]
}
```

---

## 4. 制約・ルール
- `requested_at <= completed_at`（UTC）
- `executed_qty = sum(fills.qty)`（丸め差は±最小ステップまで許容）
- `avg_price` が存在する場合、`cost ≈ executed_qty * avg_price`（手数料含めるなら注記）
- `fills` は**空配列不可**（error 時は `executed_qty=0` と `fills=[]` を許容）
- `reason_code` 候補（Do-Layer）:
  - `IDEMPOTENCY_CONFLICT`, `VALIDATION_ERROR`,  
    `BROKER_REJECTED`, `BROKER_TIMEOUT`, `BROKER_DOWN`, `INTERNAL_ERROR`

---

## 5. result_digest（幂等台帳用）
`idempo_ledger.result_digest` は以下の**正規化手順**で生成する。

1. `ExecResult` から **可変メタ**を除外（例: `latency_ms.total` の微小差は含めてもよいが、実装で固定）  
2. 以下の**安定キー**のみを抽出して JSON 正規化（キーソート・無駄空白排除）  
   - `status, order_id, instrument, side, executed_qty, avg_price, fills, reason_code`  
3. `SHA-256` でハッシュ化し `sha256:<hex>` を格納

Python擬似:
```python
def result_digest(exec_result: dict) -> str:
    stable = {
      "status": exec_result["status"],
      "order_id": exec_result["order_id"],
      "instrument": exec_result["instrument"],
      "side": exec_result["side"],
      "executed_qty": exec_result.get("executed_qty", 0),
      "avg_price": exec_result.get("avg_price"),
      "fills": exec_result.get("fills", []),
      "reason_code": exec_result.get("reason_code")
    }
    j = json.dumps(stable, sort_keys=True, separators=(",",":")).encode()
    return "sha256:" + hashlib.sha256(j).hexdigest()
```

---

## 6. 幂等との関係
- `/do/order` は **完全一致再送→200 で前回の `ExecResult`** を返す。  
- `result_digest` は 200 応答再利用の同一性検証やデバッグに利用。

---

## 7. 後方互換
- v1.0 初版。将来の拡張は**任意フィールドの追加**のみを原則とし、既存キーの意味変更は不可。

---

## 8. 変更履歴
- **2025-08-24**: 初版公開。正規化手順とエラーコードを定義。
