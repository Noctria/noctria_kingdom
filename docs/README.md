# 👑 Noctria Kingdom

AIによる為替戦略王国「Noctria」のトレーディングシステムへようこそ。

本プロジェクトは、複数のAI戦略（臣下）と統合判断AI（王）が連携し、Airflowを通じて自律的なトレード戦略運用を実現する大規模AIトレーディングシステムです。

## 📁 ドキュメント構成

- [構成図と全体概要](docs/architecture.md)
- [戦略AIの仕様](docs/strategy_manual.md)
- [データ処理と学習パイプライン](docs/data_handling.md)
- [最適化・強化学習の記録](docs/optimization_notes.md)

## ✨ クイックスタート

```bash
cd airflow-docker
docker compose up -d
```

---

🧠 構成要素
AurusSingularis: トレンド分析AI

LeviaTempest: 短期スキャルピングAI

NoctusSentinella: リスク監視AI

PrometheusOracle: ファンダメンタル予測AI

Noctria: 統合判断AI（王）
<!-- AUTODOC:BEGIN mode=git_log path_globs="README.md;docs/**/*.md" title=ドキュメント更新履歴（最近30） limit=30 since=2025-08-01 -->
### ドキュメント更新履歴（最近30）

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
- **d141a4c** 2025-08-14T03:30:22+09:00 — Update Vision-Governance.md (by Noctoria)
  - `docs/governance/Vision-Governance.md`
- **dc7a660** 2025-08-14T03:26:59+09:00 — Update Vision-Governance.md (by Noctoria)
  - `docs/governance/Vision-Governance.md`
- **6112943** 2025-08-14T03:23:05+09:00 — Update howto-*.md (by Noctoria)
  - `docs/howto/howto-*.md`
- **f167207** 2025-08-14T03:16:58+09:00 — Update Testing-And-QA.md (by Noctoria)
  - `docs/qa/Testing-And-QA.md`
- **8021926** 2025-08-14T03:12:38+09:00 — Update Roadmap-OKRs.md (by Noctoria)
  - `docs/roadmap/Roadmap-OKRs.md`
- **05194d5** 2025-08-14T03:09:18+09:00 — Update ModelCard-Prometheus-PPO.md (by Noctoria)
  - `docs/models/ModelCard-Prometheus-PPO.md`
- **1bd84f1** 2025-08-14T03:04:19+09:00 — Update Release-Notes.md (by Noctoria)
  - `docs/roadmap/Release-Notes.md`
- **02b8516** 2025-08-14T02:56:00+09:00 — Update Config-Registry.md (by Noctoria)
  - `docs/operations/Config-Registry.md`
- **1a4b22e** 2025-08-14T02:50:27+09:00 — Update Runbooks.md (by Noctoria)
  - `docs/operations/Runbooks.md`
- **33dd76d** 2025-08-14T02:46:28+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **f1f2743** 2025-08-14T02:42:05+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **32ae51d** 2025-08-14T02:35:42+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **01fec3a** 2025-08-14T02:31:01+09:00 — Update 00-INDEX.md (by Noctoria)
  - `docs/00_index/00-INDEX.md`
- **3f7b49d** 2025-08-14T02:19:26+09:00 — Update 00-INDEX.md (by Noctoria)
  - `docs/00_index/00-INDEX.md`
- **7e68901** 2025-08-13T21:26:36+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **ff8d8c2** 2025-08-13T16:54:25+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **93b1ef1** 2025-08-13T12:09:58+09:00 — Rename Next Actions — Noctria PDCA Hardening Plan to Next Actions — Noctria PDCA Hardening Plan.md (by Noctoria)
  - `"docs/Next Actions \342\200\224 Noctria PDCA Hardening Plan.md"`
- **2e20d48** 2025-08-13T11:55:12+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **cb308f7** 2025-08-13T01:39:56+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **23940b4** 2025-08-13T00:43:38+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **8faf489** 2025-08-13T00:24:16+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **80783ed** 2025-08-13T00:22:34+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **602e45d** 2025-08-12T23:57:03+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **7116954** 2025-08-12T23:44:44+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **9a3c459** 2025-08-12T23:02:47+09:00 — Update Do-Layer-Contract.md (by Noctoria)
  - `docs/apis/Do-Layer-Contract.md`
- **ce87e75** 2025-08-12T22:54:25+09:00 — Update Testing-And-QA.md (by Noctoria)
  - `docs/qa/Testing-And-QA.md`
<!-- AUTODOC:END -->
