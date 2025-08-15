# 🗓 Release Notes — Noctria Kingdom

**Document Version:** 1.1  
**Status:** Adopted  
**Last Updated:** 2025-08-14 (JST)

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
- [ ] **Outbox**（Do 層の冪等化キュー）実装とスイッチ導入（`do.idempotency.outbox_enabled`）  
- [ ] GUI RBAC（`auth.provider: oidc`）準備

---

## 2025.08-p1 “Ops Hardening” — GUI systemd/ENV & Observability
**リリース日:** 2025-08-14 (JST)  
**対象:** 運用安定化（systemd 経由 GUI 起動の標準化、ENV 注入、可観測性の配線整備）。機能破壊なし。

### 🧭 Highlights
- **GUI 起動方式を systemd 標準化**：ENV 展開の不具合を解消し、再起動/監査を一貫化。  
- **既定ポートを 8001 に更新**（ENV: `NOCTRIA_GUI_PORT` で上書き可）。  
- **ENV ファイル** `/etc/default/noctria-gui` を **SoT** として採用（DSN/PORT）。  
- **Observability 追補**：`obs_decisions` / `obs_exec_events` をドキュメントに反映、GUI ルート `/pdca/timeline`, `/pdca/latency/daily` を明記。  
- ドキュメント群を最新版に更新（Mermaid の互換レンダリング修正含む）。

### ✨ New (追加)
- **systemd ユニット推奨形**（ENV 展開のため **/bin/sh -lc** 経由）：
  ```ini
  [Service]
  EnvironmentFile=/etc/default/noctria-gui
  Environment=PYTHONUNBUFFERED=1
  WorkingDirectory=/mnt/d/noctria_kingdom
  ExecStart=/bin/sh -lc 'exec /mnt/d/noctria_kingdom/venv_gui/bin/gunicorn \
    --workers 4 --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${NOCTRIA_GUI_PORT:-8001} \
    --access-logfile - --error-logfile - \
    noctria_gui.main:app'
  Restart=always
  ```
- **ENV ファイル（標準）**：
  ```dotenv
  NOCTRIA_OBS_PG_DSN=postgresql://noctria:noctria@127.0.0.1:55432/noctria_db
  NOCTRIA_GUI_PORT=8001
  ```

### 🔧 Improvements (改善)
- **Config Registry v1.1**：GUI 既定ポートを 8001 に更新、systemd/ENV 運用を正式化。  
- **Architecture Overview v1.2.5**：図版リンクを `diagrams/*.mmd` に分離、Mermaid 構文を GitHub 互換へ修正。  
- **Observability（最新版）**：テーブル/ビュー（`obs_decisions`, `obs_exec_events`, `obs_trace_timeline` 等）と GUI ルートを反映。  
- Runbooks に **systemd 起動/確認コマンド**を追補（`systemctl show -p Environment*`, `ss -ltnp | grep :8001`）。

### 🛡 Security / Governance
- Secrets は引き続き **ENV/Vault** のみ（Git への混入禁止）。  
- 運用変更（ポート/ユニット）は **Two-Person + King** で承認。

### 🔌 API / Contract
- 変更なし（**互換**）。GUI バインドポートの既定値のみ変更（プロキシ/ALB の転送先を要確認）。

### ⚠️ Breaking Changes（互換注意）
- **GUI 既定ポート**：`8000 → 8001`。  
  - 影響：FW/ALB/プロキシ/コンテナの **ポート定義更新** が必要な場合あり。  
  - API/ルート構造の変更は **なし**。

### 🔁 Migration Checklist（移行チェック）
- [ ] `/etc/default/noctria-gui` を作成（**LF/644/root:root**、CRLF 注意）  
- [ ] `sudo systemctl daemon-reload && sudo systemctl restart noctria_gui`  
- [ ] 反映確認：  
  ```bash
  sudo systemctl show -p EnvironmentFiles -p Environment -p ExecStart noctria_gui
  ss -ltnp | grep ':8001'
  curl -sS http://127.0.0.1:${NOCTRIA_GUI_PORT:-8001}/healthz
  ```
- [ ] 逆プロキシ/ファイアウォール/ALB のポート更新（必要時）  
- [ ] `docs/operations/Runbooks.md` / `Config-Registry.md` の参照リンクが新仕様になっていることを確認

### 🧪 QA / 運用ベリファイ
- **再起動耐性**：`Restart=always` 動作確認（連続 3 回再起動で安定）。  
- **ENV 展開**：`NOCTRIA_GUI_PORT` が `ExecStart` に反映されることを `journalctl -u noctria_gui` で確認。  
- **観測**：`/pdca/timeline`, `/pdca/latency/daily` が GUI で表示されること。

### 🐞 Known Issues（既知の課題）
- 大規模バックフィル時の I/O 飽和（Storage IOPS に留意、Runbooks §12 を遵守）。  
- 一部ブローカーのレート制限が厳格（指数バックオフを推奨）。  
- ダッシュボードの “段階導入注釈” は現状手動（Unreleased で自動化予定）。

### 📌 Post-Release Actions（リリース後タスク）
- [ ] 7 日間の KPI 監視（`win_rate`, `max_dd_pct`, `do_order_latency_seconds`）。  
- [ ] 逆プロキシ設定の棚卸し（8001 対応漏れをゼロに）。  
- [ ] 監査：`systemd` ユニット変更の記録（適用者・時刻・差分）を残す。

### 🙌 Acknowledgments
現場の Ops チームと GUI/Infra を繋いでくれた皆さんに感謝。ENV 展開の不具合潰しとドキュメント整理、最高でした。

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
- **2025-08-14:** `2025.08-p1 "Ops Hardening"` を追加。Document Version を 1.1 に更新。  
- **2025-08-12:** 章立て/テンプレ確立、`2025.08 "Foundation"` を登録

<!-- AUTOGEN:CHANGELOG START -->

### 🛠 Updates since: `2025-08-13 18:04 UTC`

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
<!-- AUTODOC:BEGIN mode=git_log path_globs=docs/roadmap/*.md title="Release Notes 更新履歴（最近50）" limit=50 since=2025-07-01 -->
### Release Notes 更新履歴（最近50）

- **e79166f** 2025-08-16T00:51:44+09:00 — docs: full-wrap AUTODOC + sync from partials (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/00_index/00-INDEX.md.bak`
  - `"docs/Next Actions \342\200\224 Noctria PDCA Hardening Plan.md"`
  - `"docs/Next Actions \342\200\224 Noctria PDCA Hardening Plan.md.bak"`
  - `docs/Noctria_Kingdom_System_Design_v2025-08.md`
  - `docs/Noctria_Kingdom_System_Design_v2025-08.md.bak`
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
- **8021926** 2025-08-14T03:12:38+09:00 — Update Roadmap-OKRs.md (by Noctoria)
  - `docs/roadmap/Roadmap-OKRs.md`
- **1bd84f1** 2025-08-14T03:04:19+09:00 — Update Release-Notes.md (by Noctoria)
  - `docs/roadmap/Release-Notes.md`
- **c193ed7** 2025-08-12T16:09:23+09:00 — Roadmap-OKRs.md を更新 (by Noctoria)
  - `docs/roadmap/Roadmap-OKRs.md`
- **513e712** 2025-08-12T16:03:18+09:00 — Release-Notes.md を更新 (by Noctoria)
  - `docs/roadmap/Release-Notes.md`
- **1fc087b** 2025-08-12T03:04:38+09:00 — Create Roadmap-OKRs.md (by Noctoria)
  - `docs/roadmap/Roadmap-OKRs.md`
- **0757b67** 2025-08-12T03:04:22+09:00 — Create Release-Notes.md (by Noctoria)
  - `docs/roadmap/Release-Notes.md`
<!-- AUTODOC:END -->
