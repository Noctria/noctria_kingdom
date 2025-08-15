# 🗂 ADRs — Architecture Decision Records (Index) / Noctria Kingdom

**Document Version:** 1.0  
**Status:** Adopted  
**Last Updated:** 2025-08-14 (JST)

> このファイルは **ADRs（Architecture Decision Records）** の「索引」と「運用ルール」「テンプレート」を提供します。  
> **注意:** 本ファイルは *Coding Standards* ではありません。コーディング規約は `../governance/Coding-Standards.md` を正とします。

---

## 1) 目的と適用範囲
- **目的:** 重要な技術/運用の意思決定を小さく、追跡可能に、将来の読み手にも再現できる形で記録する。  
- **対象:** アーキテクチャ、契約/API、可観測性、セキュリティ、データ管理、運用方式（Airflow/DAG）、ガードレール（Noctus）など。  
- **非対象:** 単純なバグ修正や明白なリファクタリング（ただし影響が広ければ ADR 化を検討）。

---

## 2) 形式とディレクトリ
- **場所:** `docs/adrs/`  
- **命名規則:** `ADR-YYYYMMDD-xxxx-snake-case-title.md`  
  - `YYYYMMDD` は決定日、`xxxx` は 4 桁の連番（同日内で昇順）。  
  - 例: `ADR-20250814-0001-json-schema-as-contract.md`
- **リンク:** ADR 同士は相互に相対パスでリンク（`Supersedes:` / `Superseded-by:` を明記）。  
- **言語:** 日本語を基本。必要に応じて短い英語併記可。

---

## 3) ステータス遷移（Lifecycle）
- `Proposed` → レビュー中（PR 上で議論）  
- `Accepted` → 合意し採用。実装/運用ルールに反映。  
- `Rejected` → 採用しない。理由を記録。  
- `Deprecated` → 将来の廃止予定。移行ガイド必須。  
- `Superseded` → 後続 ADR に置換。リンク必須。

---

## 4) いつ ADR を書くか（トリガ）
- **契約/API/スキーマ**の変更（特に Breaking / `/v2` 導入）  
- **可観測性**の基本方針（メトリクス SoT、保持、アラート基準）  
- **セキュリティ/アクセス**（Two-Person Gate、Secrets 運用）  
- **運用方式**（Airflow キュー分離、リトライ/冪等）、**データ保持**  
- **実装原則**（Idempotency-Key 必須、Correlation-ID 貫通、Outbox パターン等）

> 迷ったら **書く**。短くても記録することに価値があります。

---

## 5) テンプレート（コピーして使用）
```md
# ADR-YYYYMMDD-xxxx — {短い決定タイトル}

**Status:** Proposed | Accepted | Rejected | Deprecated | Superseded  
**Date:** YYYY-MM-DD  
**Owners:** {role or people}  
**Supersedes:** ./ADR-YYYYMMDD-xxxx-*.md (あれば)  
**Superseded-by:** ./ADR-YYYYMMDD-xxxx-*.md (あれば)

## Context
- 背景・問題・制約・代替案を簡潔に。関連 Issue/PR/ドキュメント（相対リンク）:
  - ../architecture/Architecture-Overview.md
  - ../observability/Observability.md
  - ../operations/Config-Registry.md
  - ../apis/Do-Layer-Contract.md など

## Decision
- 何を採用/却下するか、**短い要点**で確定文。
- 影響範囲（コード/運用/セキュリティ/スキーマ）も列挙。

## Consequences
- プラス/マイナス/トレードオフ。
- 運用変更（Runbooks 追記点）、監視・SLO への影響。

## Rollout / Migration
- 段階導入（7%→30%→100%）、移行ガイド、ロールバック手順。
- 互換性（SemVer / `/v1` 併存期限）、テスト/契約検証。

## References
- 参考リンク、前提となる ADR、外部標準/仕様など。
```

---

## 6) 運用ルール（Docs-as-Code）
- **PR 同梱:** ADR は **関連コード/設定/Runbooks の変更と同一 PR** で提出。  
- **Two-Person Gate:** `risk_policy / flags / API / Do-Contract / Schemas` の重大変更は **二人承認 + King**。  
- **SemVer:** 契約/スキーマは後方互換を基本。Breaking は `/v2` を併存、移行ガイド必須（`Release-Notes.md` に明記）。  
- **参照の一貫性:** ADR で決めた内容は、`Architecture-Overview.md` / `Observability.md` / `Config-Registry.md` 等へ即反映。  
- **可観測性:** 決定ごとに必要なメトリクス/アラート更新を伴う場合は `deploy/alerts/*` の差分を含める。

---

## 7) レビュー観点チェックリスト
- [ ] **問題設定が明確**（誰が何に困っているか / 制約は何か）  
- [ ] **選択肢の比較**（少なくとも 2–3 案の検討跡）  
- [ ] **決定/非決定の境界が明確**（スコープ外は明記）  
- [ ] **運用/監視/セキュリティへの影響**が整理されている  
- [ ] **ロールアウト/ロールバック手順**が現実的  
- [ ] **関連文書/契約の更新**が同 PR に含まれる  
- [ ] **Two-Person Gate** 対象なら承認者が揃っている

---

## 8) 直近の重要トピック（ADR 候補 / 既決の明文化）
> まだ個別 ADR がないものは **候補**として列挙。順次 ADR 化します。

- **ADR-20250814-0001 — JSON Schema を公式契約とし SemVer 運用**（/api/v1、Breaking は /v2 併存）【候補】  
- **ADR-20250814-0002 — Idempotency-Key の書き込み系必須化（24h 冪等）**【候補】  
- **ADR-20250814-0003 — Correlation-ID（trace_id）の P→D→Exec 貫通**（`X-Trace-Id` / DB obs_*）【候補】  
- **ADR-20250814-0004 — Noctus Gate を Do 層の強制境界として適用**（バイパス禁止）【候補】  
- **ADR-20250814-0005 — Observability SoT（obs_* テーブル + ロールアップ方針）**【候補】  
- **ADR-20250814-0006 — 段階導入曲線 7%→30%→100% を標準化**（Safemode 併用）【候補】  
- **ADR-20250814-0007 — DO 層の Outbox + Idempotency-Key で少なくとも「once」保証**【候補】  
- **ADR-20250814-0008 — 内部時刻は UTC 固定 / 表示は GUI で TZ 補正**【候補】  
- **ADR-20250814-0009 — Airflow キュー分離（critical_do / models）と SLO**【候補】

> 上記は `Architecture-Overview.md` / `Observability.md` / `Runbooks.md` 等に既に記述があり、**ADR としての単体記録**を追加予定です。

---

## 9) 既存ドキュメントとの関係（Cross-Refs）
- アーキテクチャ: `../architecture/Architecture-Overview.md`, `../architecture/Plan-Layer.md`  
- 運用: `../operations/Runbooks.md`, `../operations/Airflow-DAGs.md`, `../operations/Config-Registry.md`  
- 契約/API: `../apis/API.md`, `../apis/Do-Layer-Contract.md`  
- 可観測性: `../observability/Observability.md`  
- セキュリティ: `../security/Security-And-Access.md`  
- QA: `../qa/Testing-And-QA.md`  
- 計画: `../roadmap/Roadmap-OKRs.md`, `../roadmap/Release-Notes.md`

---

## 10) よくある質問（FAQ）
- **Q:** Issue/PR の議論と何が違う？  
  **A:** ADR は**決定の最終形**と**理由**を将来に残す永久記録。議論ログは散逸しがち。  
- **Q:** 小さな変更でも必要？  
  **A:** 影響が広い/戻しにくい/契約や運用方針に触れるなら ADR を推奨。  
- **Q:** 既存の暗黙の方針は？  
  **A:** 今後の変更時に**確定情報として ADR 化**。後追い ADR も価値があります。

---

## 11) 作成ショートカット（任意）
```bash
# 新規 ADR 作成の雛形出力例
d=docs/adrs && today=$(date +%Y%m%d) && seq=0001 && \
cat > $d/ADR-${today}-${seq}-short-title.md <<'EOF'
# ADR-YYYYMMDD-xxxx — {短い決定タイトル}

**Status:** Proposed  
**Date:** YYYY-MM-DD  
**Owners:** {role or people}

## Context
...

## Decision
...

## Consequences
...

## Rollout / Migration
...

## References
...
EOF
```

---

## 12) 変更履歴
- **2025-08-14:** v1.0 初版（索引/運用ルール/テンプレ/候補一覧）。  
  旧内容に *Coding Standards* が含まれていたため、該当内容は `../governance/Coding-Standards.md` を正とする方針を明記。

<!-- AUTOGEN:CHANGELOG START -->

### 🛠 Updates since: `2025-08-13 18:33 UTC`

- `4715c7b` 2025-08-15T05:12:32+09:00 — **Update update_docs_from_index.py** _(by Noctoria)_
  - `scripts/update_docs_from_index.py`
- `c20a9bd` 2025-08-15T04:58:31+09:00 — **Create update_docs_from_index.py** _(by Noctoria)_
  - `scripts/update_docs_from_index.py`
- `969f987` 2025-08-15T04:36:32+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `a39c7db` 2025-08-15T04:14:15+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `09a3e13` 2025-08-15T03:51:14+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `aea152c` 2025-08-15T03:34:12+09:00 — **Update strategy_detail.py** _(by Noctoria)_
  - `noctria_gui/routes/strategy_detail.py`
- `3bc997c` 2025-08-15T03:23:40+09:00 — **Update strategy_detail.py** _(by Noctoria)_
  - `noctria_gui/routes/strategy_detail.py`
- `482da8a` 2025-08-15T03:02:26+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `feef06f` 2025-08-15T02:33:44+09:00 — **Update docker-compose.yaml** _(by Noctoria)_
  - `airflow_docker/docker-compose.yaml`
- `e4e3005` 2025-08-15T02:15:13+09:00 — **Update __init__.py** _(by Noctoria)_
  - `noctria_gui/__init__.py`
- `4b38d3b` 2025-08-15T01:48:52+09:00 — **Update path_config.py** _(by Noctoria)_
  - `src/core/path_config.py`
- `00fc537` 2025-08-15T01:44:12+09:00 — **Create kpi_minidemo.py** _(by Noctoria)_
  - `src/plan_data/kpi_minidemo.py`
- `daa5865` 2025-08-15T01:37:54+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `5e52eca` 2025-08-15T01:35:28+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `e320246` 2025-08-15T01:34:39+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `de39f94` 2025-08-15T01:33:29+09:00 — **Create Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `e4c82d5` 2025-08-15T01:16:27+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `47a5847` 2025-08-15T01:06:11+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `15188ea` 2025-08-15T00:59:08+09:00 — **Update __init__.py** _(by Noctoria)_
  - `noctria_gui/__init__.py`
- `1b4c2ec` 2025-08-15T00:41:34+09:00 — **Create statistics_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/statistics_routes.py`
- `49795a6` 2025-08-15T00:34:44+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `4d7dd70` 2025-08-15T00:28:18+09:00 — **Update act_service.py** _(by Noctoria)_
  - `src/core/act_service.py`
- `1d38c3c` 2025-08-14T22:21:33+09:00 — **Create policy_engine.py** _(by Noctoria)_
  - `src/core/policy_engine.py`
- `dcdd7f4` 2025-08-14T22:15:59+09:00 — **Update airflow_client.py** _(by Noctoria)_
  - `src/core/airflow_client.py`
- `e66ac97` 2025-08-14T22:08:25+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `6c49b8e` 2025-08-14T21:58:17+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `e0b9eaa` 2025-08-14T21:53:00+09:00 — **Update pdca_summary_service.py** _(by Noctoria)_
  - `src/plan_data/pdca_summary_service.py`
- `368203e` 2025-08-14T21:44:48+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `cc9da23` 2025-08-14T21:32:42+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `434d2e2` 2025-08-14T21:23:55+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `d0df823` 2025-08-14T21:18:54+09:00 — **Update decision_registry.py** _(by Noctoria)_
  - `src/core/decision_registry.py`
- `1eaed26` 2025-08-14T21:08:01+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `b557920` 2025-08-14T21:03:59+09:00 — **Update strategy_evaluator.py** _(by Noctoria)_
  - `src/core/strategy_evaluator.py`
- `0c7a12f` 2025-08-14T21:00:00+09:00 — **Create decision_registry.py** _(by Noctoria)_
  - `src/core/decision_registry.py`
- `2f034a5` 2025-08-14T20:58:16+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `28bb890` 2025-08-14T20:51:37+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `307da2d` 2025-08-14T20:49:15+09:00 — **Create act_service.py** _(by Noctoria)_
  - `src/core/act_service.py`
- `bf993f3` 2025-08-14T20:41:12+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `4b7ca22` 2025-08-14T20:35:18+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `3880c7b` 2025-08-14T20:32:42+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `074b6cf` 2025-08-14T20:24:03+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `46d639d` 2025-08-14T20:17:49+09:00 — **Update strategy_evaluator.py** _(by Noctoria)_
  - `src/core/strategy_evaluator.py`
- `f63e897` 2025-08-14T20:12:50+09:00 — **Update veritas_recheck_dag.py** _(by Noctoria)_
  - `airflow_docker/dags/veritas_recheck_dag.py`
- `7c3785e` 2025-08-14T20:08:26+09:00 — **Create veritas_recheck_all_dag.py** _(by Noctoria)_
  - `airflow_docker/dags/veritas_recheck_all_dag.py`
- `49fe520` 2025-08-14T15:41:00+09:00 — **main.py を更新** _(by Noctoria)_
  - `noctria_gui/main.py`
- `3648612` 2025-08-14T15:35:27+09:00 — **pdca_routes.py を更新** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `f7f1972` 2025-08-14T06:32:19+09:00 — **Update base_hud.html** _(by Noctoria)_
  - `noctria_gui/templates/base_hud.html`
- `eae18c6` 2025-08-14T06:21:35+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `1d6047c` 2025-08-14T06:10:33+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `3c55ed0` 2025-08-14T06:04:20+09:00 — **Create dammy** _(by Noctoria)_
  - `noctria_gui/static/vendor/dammy`
- `7b4624d` 2025-08-14T05:45:03+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `35e4c50` 2025-08-14T04:49:16+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `6c88b9f` 2025-08-14T04:31:58+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `1a0b00e` 2025-08-14T04:29:17+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `2b51ef9` 2025-08-14T04:27:11+09:00 — **Create pdca_summary_service.py** _(by Noctoria)_
  - `src/plan_data/pdca_summary_service.py`
- `6ff093a` 2025-08-14T04:24:34+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `7e2e056` 2025-08-14T04:20:51+09:00 — **Create pdca_control.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_control.html`
- `cf248ee` 2025-08-14T04:15:18+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `d8e0d6e` 2025-08-14T04:12:02+09:00 — **Create airflow_client.py** _(by Noctoria)_
  - `src/core/airflow_client.py`

<!-- AUTOGEN:CHANGELOG END -->
<!-- AUTODOC:BEGIN mode=git_log path_globs=docs/adrs/*.md title=ADRファイルの更新履歴（最近50） limit=50 since=2025-07-01 -->
### ADRファイルの更新履歴（最近50）

- **51ddf2a** 2025-08-15T19:53:46+09:00 — docs: AUTODOCブロック挿入および本文更新 (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/00_index/00-INDEX.md.bak`
  - `docs/README.md`
  - `docs/README.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md`
  - `docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md`
  - `docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/03_entities_schemas.md`
  - `docs/_partials/apis/Do-Layer-Contract/03_entities_schemas.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/04_order_request.md`
  - `docs/_partials/apis/Do-Layer-Contract/04_order_request.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/05_exec_result.md`
  - `docs/_partials/apis/Do-Layer-Contract/05_exec_result.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/06_audit_order.md`
  - `docs/_partials/apis/Do-Layer-Contract/06_audit_order.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md`
  - `docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md`
  - `docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md.bak`
- **7111b30** 2025-08-15T19:38:34+09:00 — docs: AUTODOCブロック挿入および本文更新 (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/00_index/00-INDEX.md.bak`
  - `docs/README.md`
  - `docs/README.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md`
  - `docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md`
  - `docs/_partials/apis/Do-Layer-Contract/03_entities_schemas.md`
  - `docs/_partials/apis/Do-Layer-Contract/04_order_request.md`
  - `docs/_partials/apis/Do-Layer-Contract/05_exec_result.md`
  - `docs/_partials/apis/Do-Layer-Contract/06_audit_order.md`
  - `docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md`
  - `docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md`
  - `docs/_partials/apis/Do-Layer-Contract/09_error_codes.md`
  - `docs/_partials/apis/Do-Layer-Contract/10_samples_min.md`
  - `docs/_partials/apis/Do-Layer-Contract/11_contract_tests.md`
  - `docs/_partials/apis/Do-Layer-Contract/12_changelog.md`
  - `docs/adrs/ADRs.md`
  - `docs/adrs/ADRs.md.bak`
  - `docs/apis/Do-Layer-Contract.md`
  - `docs/apis/Do-Layer-Contract.md.bak`
- **30ae379** 2025-08-15T18:55:06+09:00 — 📄 AutoDoc: update docs from index (by Veritas Machina)
  - `action`
  - `data/decisions/ledger.csv`
  - `data/models/prometheus/PPO/obs8/latest`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:18:10+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:18:10+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:19:41+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:19:41+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:22:19+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:22:19+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:33:11+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:33:11+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T15:44:05+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T15:44:05+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:20:12.935706+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:20:12.935706+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:21:36.023694+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:21:36.023694+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:27:02.701382+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:27:02.701382+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T17:21:59.539332+00:00/metadata.json`
- **d09c7ae** 2025-08-15T05:31:20+09:00 — docs: update from 00-INDEX.md sync (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/_generated/update_docs.log`
  - `docs/adrs/ADRs.md`
  - `docs/apis/API.md`
  - `docs/apis/Do-Layer-Contract.md`
  - `docs/apis/observability/Observability.md`
  - `docs/architecture/Architecture-Overview.md`
  - `docs/architecture/Plan-Layer.md`
  - `docs/governance/Coding-Standards.md`
  - `docs/governance/Vision-Governance.md`
  - `docs/incidents/Incident-Postmortems.md`
  - `docs/models/ModelCard-Prometheus-PPO.md`
  - `docs/models/Strategy-Lifecycle.md`
  - `docs/observability/Observability.md`
  - `docs/operations/Airflow-DAGs.md`
  - `docs/operations/Config-Registry.md`
  - `docs/operations/Runbooks.md`
  - `docs/qa/Testing-And-QA.md`
  - `docs/risks/Risk-Register.md`
  - `docs/roadmap/Release-Notes.md`
- **c29388a** 2025-08-14T03:33:49+09:00 — Update ADRs.md (by Noctoria)
  - `docs/adrs/ADRs.md`
- **8bdcdaf** 2025-08-12T17:15:26+09:00 — Rename ADRs to ADRs.md (by Noctoria)
  - `docs/adrs/ADRs.md`
<!-- AUTODOC:END -->
