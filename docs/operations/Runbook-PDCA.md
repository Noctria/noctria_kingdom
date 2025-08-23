# Runbook: PDCA Recheck & Adopt (v1.1 aligned)
**Last Updated:** 2025-08-24 (JST)

---

## 0. 概要
PDCA サイクルの「Recheck（再評価）」および「Adopt（採用）」の標準運用手順。  
Airflow DAG と KingNoctria を経由して実行され、幂等性は **OrderRequest v1.1（idempotency_key）** と **idempo_ledger** で担保される。

### 0.1 Idempotency（前提）
- 本運用は **OrderRequest v1.1** を前提とする。  
- **ヘッダ `Idempotency-Key` と `body.idempotency_key` は一致必須**。  
- 同一キー再送は **完全一致→200**、**差分あり→409**。  
- 詳細: `docs/architecture/contracts/OrderRequest.md` / `docs/apis/Do-Layer-Contract.md`

---

## 1. Recheck（再評価）
1. GUI → [POST] `/pdca/recheck`  
   - body 例:  
     ```json
     {
       "strategy_id": "strat-xyz",
       "window": "2024-01-01..2025-08-24",
       "reason": "weekly-review"
     }
     ```
2. King → Airflow DAG `pdca_recheck_all` を起動  
   - conf 例:  
     ```json
     {
       "trace_id": "trace-2025-08-24-070000-jst-xxxxx",
       "reason": "weekly-review",
       "filters": { "strategy_tags": ["veritas","candidate"] },
       "ttl_hours": 24
     }
     ```
3. Strategies → Do 層へテスト注文  
   - **OrderRequest v1.1（ヘッダ `Idempotency-Key` と `body.idempotency_key` の一致必須）** でペーパートレードを実施。  
4. Check 層で KPI 集計 → 候補セット生成  
5. Act 層で採用提案（King 承認待ち）  

### 失敗リカバリ
- DAG タスク失敗 → Airflow の再試行ポリシー（推奨: 3 回、指数バックオフ）  
- 途中失敗時は `trace_id` をキーに `obs_plan_runs` / `obs_infer_calls` を追跡  
- 幂等衝突時は `idempo_ledger` の `status` と `response_payload_json` を参照  

---

## 2. Adopt（採用）
1. GUI → [POST] `/act/adopt`  
   - body 例:  
     ```json
     {
       "strategy_id": "strat-xyz",
       "score": 0.87,
       "reason": "stable-performance"
     }
     ```
2. Decision Registry へ追記  
3. Git タグ付与 → `adopt/<strategy>/<yyyymmdd>`  
4. HUD 更新  
5. 差し戻しが必要な場合は `rollback/<strategy>/<tag>` を作成し、King 承認で復位  

---

## 3. 運用メモ
- `ttl_hours` → DAG 内で「再入防止」兼「期限切れ後の再評価許可」に利用  
- `idempo_ledger` → 24h 経過で定期ジョブ削除（推奨: cron or Airflow sensor）  
- 採用・差し戻しは常に King 承認を経ることで統治一貫性を担保する  
