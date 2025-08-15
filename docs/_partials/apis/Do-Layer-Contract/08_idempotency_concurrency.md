<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md title="Idempotency / Concurrency" -->
### Idempotency / Concurrency

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md title="Idempotency / Concurrency" -->
### Idempotency / Concurrency

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md title="Idempotency / Concurrency" -->
### Idempotency / Concurrency

- ヘッダ `Idempotency-Key` を**必須**（24h 保持）。  
- **完全一致**でない同一キーは `409 IDEMPOTENCY_KEY_CONFLICT`。  
- 同一キー再送は**最初の結果**を**そのまま返却**。`audit_order` は**追記なし**。

---
<!-- AUTODOC:END -->
