# Component: BrokerAdapter — 送信抽象と例外マッピング
**Status:** Draft → Stable candidate  
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Do-Layer / Execution Team

---

## 0. 目的
Do 層からブローカー（実口座／ペーパー）への発注送信を**抽象化**し、例外・リトライ・結果正規化を一貫して提供する。  
`/do/order`（Do-Layer-OrderAPI-Spec）と `ExecResult`（正準結果契約）に準拠。

- 参照: `docs/apis/Do-Layer-OrderAPI-Spec.md`  
- 参照: `docs/architecture/contracts/ExecResult.md`

---

## 1. I/F 定義（擬似コード）
```python
class BrokerAdapter:
    name: str  # "paper" | "real_broker_x" 等

    async def send(self, order_request: dict) -> dict:
        """OrderRequest v1.1 を受け取り、ExecResult(正準) で返す。
        例外は内部で吸収して {status:"error", reason_code:"..."} に正規化。"""
```

### 1.1 入力前提（OrderRequest v1.1）
- `instrument`, `side`, `qty`, `time_in_force`, `idempotency_key` を必須想定
- `price=null` は成行
- **Do 層側でのバリデーション済み**（最小ロット等）

### 1.2 出力（ExecResult 正準）
- 成功: `{status:"ok", fills[], executed_qty, avg_price?, cost?, broker:{name,order_ref}, latency_ms{...}}`
- 失敗: `{status:"error", reason_code, fills:[], executed_qty:0, broker:{name,...}}`

---

## 2. 例外／エラーの正規化
| 事象 | 例 | `reason_code` | HTTP（Do層） | 備考 |
|---|---|---|---|---|
| タイムアウト | 接続・応答遅延 | `BROKER_TIMEOUT` | 502/504 | ブローカーダウンと区別 |
| 接続不可 | DNS/TCPrst | `BROKER_DOWN` | 503 | 再試行は**しない**（Outbox 参照） |
| 業務NG | 銘柄停止/数量不正 | `BROKER_REJECTED` | 400/409 | 具体コードは adapter 内ログへ |
| 検証失敗 | ローカル TIF/qty | `VALIDATION_ERROR` | 422 | Do 層の事前検証漏れ |
| 内部異常 | 想定外例外 | `INTERNAL_ERROR` | 500 | スタックはログのみ |

---

## 3. タイムアウト・リトライ方針
- **Adapter 内ではリトライしない**（P1 の Outbox パターンで担保）
- 目安タイムアウト: IOC=2.5s / FOK=5s / GTC=5s
- Circuit Breaker（任意・将来拡張）:
  - 直近 N=20 の `BROKER_TIMEOUT/BROKER_DOWN` 比率 > 50% で open（1分）

---

## 4. サンプル実装（PaperAdapter, 擬似）
```python
class PaperAdapter(BrokerAdapter):
    name = "paper"

    async def send(self, req: dict) -> dict:
        import time, random
        start = time.perf_counter()
        # 疑似約定: 100ms 以内に全量
        px = 146.120 + random.random() * 0.010
        fills = [{"px": round(px, 5), "qty": req["qty"], "ts": req["requested_at"]}]
        total = int((time.perf_counter() - start) * 1000)
        return {
            "status": "ok",
            "order_id": req["order_id"],
            "instrument": req["instrument"],
            "side": req["side"],
            "requested_at": req["requested_at"],
            "completed_at": req["requested_at"],
            "trace_id": req.get("trace_id"),
            "idempotency_key": req["idempotency_key"],
            "fills": fills,
            "avg_price": fills[0]["px"],
            "executed_qty": req["qty"],
            "cost": None,
            "slippage": None,
            "broker": {"name": self.name, "order_ref": f"paper-{req['order_id']}"},
            "latency_ms": {"queue": 0, "broker_rtt": total, "total": total},
            "reason_code": None,
            "warnings": []
        }
```

---

## 5. ロギング／メトリクス
- Logs: `adapter=name, reason_code, http_mapped, latency_ms, instrument`
- Metrics:
  - `broker.requests_total{adapter, outcome}`  
  - `broker.latency_ms{adapter}` (histogram)
  - `broker.fail_ratio{adapter}` (gauge)

---

## 6. セキュリティ
- 認証情報（API Key 等）は Secrets Manager 管理、環境変数では参照のみ
- リクエスト／レスポンスに機微情報があればマスキングして保存

---

## 7. 変更履歴
- **2025-08-24**: 初版。I/F・例外マップ・PaperAdapter 例を定義。
