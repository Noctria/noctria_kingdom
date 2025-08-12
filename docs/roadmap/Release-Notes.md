# 🗓 Release Notes — Noctria Kingdom

**Document Version:** 1.0  
**Status:** Adopted  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria Kingdom の**リリース単位**での変更点・移行手順・既知の問題を明確化し、PDCA/運用への影響を最小化する。  
> 参照：`../governance/Vision-Governance.md` / `../operations/Runbooks.md` / `../operations/Airflow-DAGs.md` / `../operations/Config-Registry.md` / `../observability/Observability.md` / `../apis/API.md` / `../apis/Do-Layer-Contract.md` / `../security/Security-And-Access.md` / `../qa/Testing-And-QA.md` / `../models/ModelCard-Prometheus-PPO.md` / `../models/Strategy-Lifecycle.md` / `../architecture/Architecture-Overview.md`

---

## 0) 読み方 & バージョニング
- 本ドキュメントは **リリース単位**に上から順に追記する（最新が最上部）。  
- プロジェクト全体の**カレンダー版**：`YYYY.MM`（必要に応じ `-patchN` を付与）。  
- 破壊的変更（Breaking）は **明示**し、`Migration Checklist` を添える。  
- ADR がある変更は `adrs/` を必ずリンク。

---

## Unreleased（次回リリースの下書き）
**予定タグ:** `2025.09`  
**候補:**  
- [ ] Airflow 本番キュー分離（`critical_do` / `models`）  
- [ ] `Do-Layer-Contract` の小改定（`meta.shadow` の必須化検討）  
- [ ] KPI スキーマのバージョンタグ導入（`kpi_summary.schema.json` に `schema_version`）  
- [ ] Observability ダッシュボードの “段階導入注釈” 自動投入

---

## 2025.08 “Foundation” — 初期整備リリース
**リリース日:** 2025-08-12 (JST)  
**対象:** 文書/契約/運用標準の**初版整備**（コードの挙動を変える破壊的変更はなし）

### 🧭 Highlights
- 統治/運用/契約/可観測性/モデル/QA 一式の**初版ドキュメント（v1.0）**を整備。
- **ガードレール**（Non-Negotiables）と **RACI** を明文化し、運用リスクを低減。
- **Config Registry**（defaults/env/flags/secrets）の SoT（Single source of Truth）確立。
- **Do-Layer Contract** と **API v1** を提示し、Plan→Do→Check の I/F を固定。
- **Observability** のメトリクス/ルール/ダッシュボード設計を標準化。
- **Testing & QA** パイプラインの基準とゲート条件を定義。

### ✨ New (追加)
- `governance/Vision-Governance.md`：ビジョン/原則/統治モデル/RACI/テンプレ  
- `architecture/Architecture-Overview.md`：全体図/層別図リンク  
- `architecture/Plan-Layer.md`：収集→特徴量→KPI→説明の仕様  
- `operations/Runbooks.md`：SoD/EoD/抑制/ロールバック/障害プレイブック  
- `operations/Config-Registry.md`：defaults/env/flags/secrets/検証/配布  
- `operations/Airflow-DAGs.md`：DAG在庫/スケジュール/共通規約/CLI  
- `apis/API.md`：`/plan`, `/do`, `/check`, `/act`, `/config`, `/ops` の API v1  
- `apis/Do-Layer-Contract.md`：`order_request.json` / `exec_result.json` / `audit_order.json`  
- `observability/Observability.md`：ログ/メトリクス/トレース/アラートルール  
- `security/Security-And-Access.md`：RBAC/Secrets/Two-Person/監査  
- `qa/Testing-And-QA.md`：テストピラミッド/CI/ゲーティング/ゴールデン  
- `models/ModelCard-Prometheus-PPO.md`：モデル仕様/学習/評価/安全策  
- `models/Strategy-Lifecycle.md`：G0→G4 ゲート/段階導入/ロールバック  
- `risks/Risk-Register.md`：スコア規約/トップリスク/自動化/テンプレ

### 🔧 Improvements (改善)
- **用語・パス**の統一：`docs/<domain>/<Title-Case>.md` で整理。  
- **タイムゾーン規約**：内部 UTC / 表示 JST を全章で明記。  
- **段階導入の標準曲線**：7%→30%→100%（各3営業日、Safemode ON）。  
- **監査の完全性**：`audit_order.json` の推奨構造を明記（Do-Layer-Contract §7.2）。

### 🛡 Security / Governance
- **最小権限**ロール（King/Ops/Risk/Models/Arch/ReadOnly）を明文化。  
- **Secrets** を Variables に置かない原則を全章に反映。  
- **Two-Person Rule**：`risk_policy`/`flags`/`Do-Layer`/`API`/`Schemas` の重大変更は二人承認＋King。

### 🚦 DAG Schedule（初期標準・UTC）
| DAG ID | Schedule (UTC) | Owner | SLA |
|---|---|---|---|
| `pdca_plan_workflow` | `0 5 * * 1-5` | ops | 30m |
| `do_layer_flow` | `*/5 0-23 * * 1-5` | ops | 5m |
| `pdca_check_flow` | `15 16 * * 1-5` | risk | 20m |
| `pdca_act_flow` | `0 17 * * 1-5` | ops | 45m |
| `train_prometheus_obs8` | `0 3 * * 6` | models | 2h |
| `oracle_prometheus_infer_dag` | `0 6 * * 1-5` | models | 20m |

> 表示は GUI で JST 補正。詳細は `../operations/Airflow-DAGs.md` を参照。

### 🔌 API / Contract
- **API v1** 初版公開（`/api/v1`）。変更系は **Idempotency-Key** 必須。  
- **Do-Layer Contract**：`order_request` / `exec_result` / `risk_event` / `audit_order` を JSON Schema で定義。  
- スキーマ正は `docs/schemas/*.schema.json`。CI に **契約テスト**（3パターン：FILLED/PARTIAL/REJECTED）を推奨。

### 🧪 QA / CI
- **ゲート条件**（stg）：`do_order_latency_seconds` p95 ≤ 0.5s、`do_slippage_pct` p90 ≤ 0.3%、重大アラート 0。  
- **ゴールデン/再現性**：小区間で出力ハッシュ一致を確認。  
- **Observability ルール**：`promtool check rules` を CI で検証。

### ⚠️ Breaking Changes（破壊的変更）
- なし（本リリースは**標準/文書**の導入が主。既存実装へ即時の破壊的影響はありません）

### 🔁 Migration Checklist（移行チェック）
- [ ] `config/defaults.yml` と `{env}.yml` を作成/更新（`../operations/Config-Registry.md`）  
- [ ] Airflow Variables/Connections を同期（`env`, `flags`, `risk_policy` ほか）  
- [ ] `observability` のルールファイルをデプロイ（`deploy/alerts/noctria.rules.yml`）  
- [ ] API Gateway/GUI に 2FA/OIDC を設定（`../security/Security-And-Access.md`）  
- [ ] `Runbooks.md` に従って **SoD/EoD** 手順を実施  
- [ ] `Testing-And-QA.md` の**契約/スモーク**を stg でパス  
- [ ] `Strategy-Lifecycle.md` のテンプレで現行戦略の**状態を登録**  
- [ ] 必要に応じ `ADRs/` を起票（重要判断）

### 🧩 Dependency Notes（情報）
- ランタイム/依存のバージョン固定方針は `requirements*.txt` / Dockerfile を正とする。  
- 依存のセキュリティ監査は `pip-audit` / `gitleaks` を CI で実施（`../qa/Testing-And-QA.md §3.9`）。

### 🐞 Known Issues（既知の課題）
- 大規模バックフィル時に I/O が飽和しやすい（`Runbooks.md §12` のスロットリング指針を遵守）。  
- 一部ブローカーのレート制限が厳格（`Do-Layer-Contract.md §5.2` の指数バックオフ参照）。  
- ダッシュボードの “段階導入注釈” は現状手動投入（次版で自動化予定）。

### 📌 Post-Release Actions（リリース後タスク）
- [ ] KPI の日次推移を 7 日観測（`kpi_win_rate`, `kpi_max_dd_pct`）。  
- [ ] ダッシュボードに “2025.08 Foundation” 注釈を追加。  
- [ ] インシデント/アラートの演習（Observability ルールの**リハーサル**）。

### 🙌 Acknowledgments
Docs-as-Code の整備に協力した Council & Ops & Risk チーム、ありがとう。  
特に **RACI/ガードレール**整備と **Do-Layer Contract** 固定に関わったメンバーに感謝。

---

## 履歴（Changelog of Release Notes）
- **2025-08-12:** 章立て/テンプレ確立、`2025.08 "Foundation"` を登録


