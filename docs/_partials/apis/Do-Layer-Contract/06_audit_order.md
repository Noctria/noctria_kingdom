<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/06_audit_order.md title="`audit_order`（WORM 監査）" -->
### `audit_order`（WORM 監査）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/06_audit_order.md title="`audit_order`（WORM 監査）" -->
### `audit_order`（WORM 監査）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/06_audit_order.md title="`audit_order`（WORM 監査）" -->
### `audit_order`（WORM 監査）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/06_audit_order.md title="`audit_order`（WORM 監査）" -->
### `audit_order`（WORM 監査）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/06_audit_order.md title="`audit_order`（WORM 監査）" -->
### `audit_order`（WORM 監査）

**完全記録**：入力/正規化/丸め/リスク判定/ブローカー応答/遅延/署名

```json
{
  "audit_id": "AUD-20250812-0001",
  "correlation_id": "6f1d3b34-....",
  "received_ts": "2025-08-12T06:58:00Z",
  "idempotency_key": "6b8f7e...f1",
  "request": {... order_request ...},
  "normalized": {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "qty_rounded": 0.5,
    "rounding": {"qty_mode": "floor", "qty_step": 0.001, "price_tick": 0.1}
  },
  "risk_eval": {
    "policy_version": "2025-08-01",
    "checks": [{"name":"max_position_qty","ok":true,"limit":2.0,"value":0.5}]
  },
  "broker": {
    "provider": "sim",
    "sent_ts": "2025-08-12T06:58:01Z",
    "response": {"orderId":"SIM-12345","status":"FILLED","avgPrice":58999.5}
  },
  "latency_ms": {"do_submit": 120, "broker": 190},
  "exec_result": {... exec_result ...},
  "signature": {"alg":"HMAC-SHA256","value":"ab12..."}
}
```

---
<!-- AUTODOC:END -->
