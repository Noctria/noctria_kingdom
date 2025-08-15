<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md title="スコープ & 原則（最新）" -->
### スコープ & 原則（最新）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md title="スコープ & 原則（最新）" -->
### スコープ & 原則（最新）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md title="スコープ & 原則（最新）" -->
### スコープ & 原則（最新）

- **対象**：`order_request`（入力）/ `exec_result`（出力）/ `audit_order`（監査）/ `risk_event`（警報）の**データ契約**。  
- **原則**：  
  1. **Guardrails First** — Noctus の `risk_policy` を**強制**（越境は**拒否**）。  
  2. **Idempotent** — 書き込みは **24h** の同一キーで**同一結果**（衝突は 409）。  
  3. **WORM 監査** — `audit_order.json` は**改変不可**（追記のみ）。  
  4. **後方互換** — フィールド追加は**互換**、Breaking は `/v2` と ADR 必須。

---
<!-- AUTODOC:END -->
