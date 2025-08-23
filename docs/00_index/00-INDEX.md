# 📜 Noctria Kingdom プロジェクト INDEX / Project Index
**Status:** Canonical / Adopt this file as the single source of truth  
**Last Updated (JST):** 2025-08-23

> 本INDEXは Noctria Kingdom の設計書・運用書の正規入口です。  
> The canonical entry point for all design & ops docs.

---

## 0. クイックアクセス / Quick Access
- 🏠 Dashboard (GUI HUD): `/dashboard`  
- 🔁 PDCA Summary: `/pdca/summary`  
- 🤖 AI Council Overview: `docs/architecture/Architecture-Overview.md`
- 🛠 Runbooks: `docs/operations/Runbooks.md`
- 🔍 Observability (API & GUI): `docs/observability/Observability.md`
- 🧭 Coding Standards: `docs/governance/Coding-Standards.md`
- 🧾 ADRs: `docs/adrs/ADRs.md`

---

## 1. ガバナンス / Governance
- **Vision & Governance**: `docs/governance/Vision-Governance.md`
- **Coding Standards**: `docs/governance/Coding-Standards.md`
- **Structure Principles**: `docs/structure_principles.md`

**運用ルール要点 / Highlights**
- `.bak` ファイルは段階的廃止（Git版管理へ）。This repo deprecates `.bak` duplicates.
- 図(Mermaid)は `docs/architecture/diagrams/` に集約。
- API系は `docs/apis/`、観測/可視化は `docs/observability/` に集約。

---

## 2. アーキテクチャ / Architecture
- **Overview**: `docs/architecture/Architecture-Overview.md`
- **Plan Layer**: `docs/architecture/Plan-Layer.md`
- **Do/Check/Act Diagrams**:  
  - `docs/architecture/diagrams/plan_layer.mmd`  
  - `docs/architecture/diagrams/do_layer.mmd`  
  - `docs/architecture/diagrams/check_layer.mmd`  
  - `docs/architecture/diagrams/act_layer.mmd`
- **System Design (v2025-08)**: `docs/Noctria_Kingdom_System_Design_v2025-08.md`

> ✅ **統合方針**: ルート直下の `Noctria全体.mmd` / `完全形.mmd` / `Noctria連携図.mmd` は  
> `architecture/diagrams/` へ移設し、ファイル名を `*_overview.mmd` に統一。

---

## 3. モデル & 戦略 / Models & Strategies
- **Model Card (Prometheus PPO)**: `docs/models/ModelCard-Prometheus-PPO.md`
- **Strategy Lifecycle**: `docs/models/Strategy-Lifecycle.md`
- **Strategy Manual**: `docs/strategy_manual.md`

---

## 4. API / Interfaces
- **Platform API**: `docs/apis/API.md`
- **Do-Layer Contract**: `docs/apis/Do-Layer-Contract.md`
- **Observability (APIs & GUI integration)**: `docs/apis/observability/Observability.md`  
  ↔ Mirrors high-level: `docs/observability/Observability.md`

> ✅ **統合方針**: `observability/Observability.md` は高レベル観点、  
> API詳細は `apis/observability/Observability.md` に記述し、相互リンクで整合。

---

## 5. オペレーション / Operations
- **Airflow DAGs Guide**: `docs/operations/Airflow-DAGs.md`
- **Runbooks**: `docs/operations/Runbooks.md`
- **Config Registry**: `docs/operations/Config-Registry.md`
- **PDCA / Act Automation**: `docs/operations/PDCA/README_Act_Automation.md`

---

## 6. 可観測性 / Observability
- **Guide (GUI & Metrics)**: `docs/observability/Observability.md`
- **API Details**: `docs/apis/observability/Observability.md`

---

## 7. セキュリティ / Security
- **Security & Access**: `docs/security/Security-And-Access.md`
- **Risk Register**: `docs/risks/Risk-Register.md`
- **Incident Postmortems**: `docs/incidents/Incident-Postmortems.md`

---

## 8. 企画・計画 / Planning
- **Roadmap & OKRs**: `docs/roadmap/Roadmap-OKRs.md`
- **Release Notes**: `docs/roadmap/Release-Notes.md`
- **Refactoring Plan (v3.0)**: `docs/Noctria Kingdom 全体リファクタリング計画（v3.0対応）`
- **Next Actions (PDCA Hardening)**: `docs/Next Actions — Noctria PDCA Hardening Plan.md`

---

## 9. データ取扱い / Data Handling
- **Data Handling**: `docs/data_handling.md`
- **Plan Feature Spec (v2025.08)**: `docs/plan_feature_spec.md`  
  ↔ シート: `docs/Noctria Kingdom Plan層 標準特徴量セット（v2025.08）`

---

## 10. テスト & 品質 / QA
- **Testing & QA**: `docs/qa/Testing-And-QA.md`
- **Diagnostics**: `docs/diagnostics/tree_snapshot.txt`, `docs/misc/latest_tree_and_functions.md`

---

## 11. 付録 / Misc & How-To
- **How-To Series**: `docs/howto/howto-*.md`
- **Docker/Airflow Notes**: `docs/misc/*Airflow*`, `docs/misc/docker_*`
- **Knowledge Base**: `docs/knowledge.md`, `_partials_full/docs/knowledge.md`

---

## 12. 生成・自動整備 / Generated & Automation
- **AutoDoc Rules**: `docs/autodoc_rules.yaml`
- **Wrap Rules**: `docs/wrap_rules.yaml`
- **Build Logs**: `docs/_build/logs/*`
- **Generated Diffs**: `docs/_generated/diff_report.md`

**運用手順 / Ops**
1. `scripts/update_docs_from_index.py` を実行して差分適用  
2. `_build/logs/changes_*.log` を確認し、重複・逸脱を修正  
3. `.bak` は削除し Git 履歴を参照（※下「整理方針」参照）

---

## 13. 整理方針 / Consolidation Policy
- **.bak 廃止**：`*.bak` は今後コミットしない。必要なら Git tag / branch で復元。
- **二重化の解消**：  
  - `observability/Observability.md`（高レベル）  
  - `apis/observability/Observability.md`（API詳細）  
  → 役割を明記し本文先頭に相互リンクを追加。
- **図面の一元化**：Mermaidは `architecture/diagrams/` 固定。
- **単一ソース原則**：INDEXが唯一のナビ。各章は「責任ファイル」を明示。

---

## 14. 変更履歴 / Changelog (Docs)
- 最新の変更ログは `docs/_build/logs/` を参照。  
  指標：変更ファイル数、追加・削除行、Broken links、二重化検出件数。

---

## 15. 次アクション / Next Actions
- [ ] `.bak` 一括整理（下のスクリプト参照）  
- [ ] Mermaid 図の移設とファイル名統一  
- [ ] `observability` 二層化の本文修正＆相互リンク追記  
- [ ] `Plan層 標準特徴量セット（v2025.08）` を `plan_feature_spec.md` と相互参照化  
- [ ] `Noctria_Kingdom_System_Design_v2025-08.md` を Overview と整合性チェック

---

### 付録A：.bak 一括整理スクリプト（安全版）
> 実行前に `git status` と `git stash push -u` 推奨。

```bash
# ドライラン（削除候補を表示）
rg -n --glob '**/*.bak' '' docs || true

# 本削除（コミット前提）
git ls-files -z 'docs/**/*.bak' | xargs -0 git rm -f
git commit -m 'docs: remove legacy .bak files (use git history instead)'
```

### 付録B：図面の移設（例）
```bash
mkdir -p docs/architecture/diagrams
git mv docs/Noctria全体.mmd docs/architecture/diagrams/all_overview.mmd
git mv docs/完全形.mmd     docs/architecture/diagrams/system_complete.mmd
git mv docs/Noctria連携図.mmd docs/architecture/diagrams/integration_overview.mmd
git mv docs/P層.mmd docs/architecture/diagrams/plan_layer.mmd
git mv docs/Do層.mmd docs/architecture/diagrams/do_layer.mmd
git mv docs/GUIツール.mmd docs/architecture/diagrams/gui_tools.mmd
```

### 付録C：Observability 二層化の本文最初に入れるテンプレ
```md
> This document is the **high-level guide** for observability (metrics, logs, dashboards).
> For API contracts and endpoints, see `docs/apis/observability/Observability.md`.
```

---
