<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/05_exec_result.md title="`exec_result`（Do → Check）" -->
### `exec_result`（Do → Check）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/05_exec_result.md title="`exec_result`（Do → Check）" -->
### `exec_result`（Do → Check）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/05_exec_result.md title="`exec_result`（Do → Check）" -->
### `exec_result`（Do → Check）

**必須**：`order_id`, `status`, `filled_qty`, `ts`  
**オプション**：`avg_price`, `fees`, `reason.code`, `slippage_pct`, `latency_ms`

```json
{
  "order_id": "SIM-12345",
  "status": "FILLED",
  "filled_qty": 0.50,
  "avg_price": 58999.5,
  "fees": 0.12,
  "slippage_pct": 0.18,
  "ts": "2025-08-12T06:58:03Z",
  "meta": {"symbol": "BTCUSDT", "strategy": "Prometheus-PPO"}
}
```

**ステータス規約**  
- `FILLED`：完全約定。`filled_qty>0` / `avg_price` 必須。  
- `PARTIAL`：一部約定＋キャンセル/期限切れ。`filled_qty>0`。  
- `REJECTED`：実行されず。`reason.code` 必須（例 `RISK_BOUNDARY_EXCEEDED`）。  
- `CANCELLED`：ユーザ/システムキャンセル。`filled_qty` は 0 または >0（部分）。

---
<!-- AUTODOC:END -->
