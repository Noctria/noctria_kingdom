<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md title=フロー（概観） -->
### フロー（概観）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md title=フロー（概観） -->
### フロー（概観）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md title=フロー（概観） -->
### フロー（概観）

```mermaid
sequenceDiagram
  autonumber
  participant PLAN as Plan (Aurus/Prometheus/Veritas)
  participant DO as Do Layer
  participant BROKER as Broker Adapter
  participant CHECK as Check
  PLAN->>DO: order_request (Idempotency-Key, Correlation-ID)
  DO->>DO: Noctus Guard (risk_policy)
  DO->>BROKER: normalized order (rounded)
  BROKER-->>DO: broker execution
  DO->>CHECK: exec_result
  DO->>DO: audit_order (WORM)
  DO-->>PLAN: error (if rejected)
```

---
<!-- AUTODOC:END -->
<!-- AUTODOC:END -->
<!-- AUTODOC:END -->
<!-- AUTODOC:END -->
