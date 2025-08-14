# 🧨 Risk Register — Noctria Kingdom

**Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の運用・アルゴ・オーケストレーションに関わる**主要リスクを可視化し、閾値・監視・緩和策**を明文化する。  
> 参照：`../governance/Vision-Governance.md` / `../operations/Runbooks.md` / `../operations/Config-Registry.md` / `../operations/Airflow-DAGs.md` / `../observability/Observability.md` / `../security/Security-And-Access.md` / `../apis/Do-Layer-Contract.md` / `../incidents/Incident-Postmortems.md` / `../adrs/`

---

## 0. 使い方（How to Use）
1) 新規リスクは**テンプレ（§6）**で起票 → PR。  
2) 重大イベント発生時は **Incident** を起票し、**再発防止策**を本表へ反映。  
3) **月次レビュー**（Council）でスコアと緩和策の妥当性を見直す。  
4) 閾値/トグルは `../operations/Config-Registry.md` を**単一情報源（SoT）**とする。

---

## 1. スコアリング規約（Likelihood × Impact）
- **Likelihood（発生確率）**: 1=稀（年1以下） / 2=低（四半期1） / 3=中（月1） / 4=高（週1） / 5=非常に高（週複数）  
- **Impact（影響度）**: 1=軽微 / 2=小 / 3=中（部分停止・軽損失） / 4=大（1日停止・有意損失） / 5=重大（安全性/財務に深刻）  
- **Score = L × I**  
- **色分け**（許容度目安）:  
  - **Red** ≥ 15（**不可**：即時の恒久対策/運用抑制が必要）  
  - **Orange** 10–14（要管理：緩和策と監視を強化）  
  - **Yellow** 6–9（監視維持）  
  - **Green** ≤ 5（容認）

> **Non-Negotiables**（`Vision-Governance.md`）に抵触するものは、スコアに関わらず**Red扱い**。

---

## 2. トップリスク一覧（要約表）
| ID | タイトル | カテゴリ | オーナー | L | I | Score | 現状 | 次回見直し |
|---|---|---|---|:-:|:-:|:-:|---|---|
| R-01 | レジームシフト（相場構造変化） | 市場 | Risk(Noctus) | 4 | 5 | **20** | 監視強化・Safemode準備 | 2025-08-31 |
| R-02 | 流動性低下/スリッページ急騰 | 市場/実行 | Ops/Do | 3 | 4 | **12** | Slippage監視/段階停止 | 2025-08-20 |
| R-03 | ブローカー/API 障害 | 外部依存 | Ops | 3 | 5 | **15** | 代替経路/レート制限対策 | 2025-08-20 |
| R-04 | データ欠損/品質劣化（Plan） | データ | Plan | 3 | 4 | **12** | 欠損フラグ/再取得 | 2025-08-18 |
| R-05 | Clock Skew/時刻整合不良 | 時刻/運用 | Ops | 2 | 3 | 6 | NTP監視/UTC原則 | 2025-09-01 |
| R-06 | Idempotency破れ/重複発注 | 実行/設計 | Do | 2 | 5 | **10** | キー必須/監査照合 | 2025-08-20 |
| R-07 | リスク境界の誤設定/バイパス | ガバナンス | Risk | 2 | 5 | **10** | Config二重承認 | 2025-08-20 |
| R-08 | モデルドリフト/過学習 | モデル | Models | 3 | 4 | **12** | WFO/定期再評価 | 2025-08-31 |
| R-09 | スキーマドリフト（Plan→Do→Check） | I/F | Arch | 3 | 3 | 9 | JSONSchema CI | 2025-08-25 |
| R-10 | Secrets漏えい/鍵期限切れ | セキュリティ | Sec | 2 | 5 | **10** | Vault/90日ローテ | 2025-08-22 |
| R-11 | Airflow スケジューラ停止/滞留 | オーケストレーション | Ops | 3 | 4 | **12** | HealthCheck/Backfill手順 | 2025-08-18 |
| R-12 | バックフィル起因のI/O飽和 | パフォーマンス | Ops | 3 | 3 | 9 | スロットリング | 2025-08-25 |
| R-13 | Config/Flags ドリフト | 構成管理 | Ops | 3 | 3 | 9 | 同一PR更新 | 2025-08-20 |
| R-14 | 規制/コンプラ変更の未追随 | 法務/外部 | Gov | 2 | 4 | 8 | ウォッチ/ADR対応 | 2025-09-10 |
| R-15 | 祝日/営業カレンダー誤設定 | 運用/データ | Plan/Ops | 2 | 3 | 6 | 二重ソース照合 | 2025-09-01 |
| R-16 | PII/センシティブログ流出 | セキュリティ | Sec | 2 | 4 | 8 | マスキング/静的検査 | 2025-08-20 |
| R-17 | 監視/アラート誤作動・未発火 | 可観測性 | Obs | 2 | 4 | 8 | ルールCI/演習 | 2025-08-22 |
| R-18 | 最適化発注バグ（optimized_order_execution） | 実装 | Do | 2 | 5 | **10** | ゴールデン/契約テスト | 2025-08-21 |

---

## 3. 詳細レコード（Mitigation / KPI / Triggers）
> **凡例**: Appetite=許容レベル（超過は自動/手動アクション）、KPI/Trigger=監視ロジック（`Observability.md` 準拠）、Status=Open/Watching/Mitigated/Accepted/Closed。

### R-01 レジームシフト（相場構造変化）
- **Category**: 市場 / **Owner**: Risk(Noctus) / **Score**: 20 (**Red**) / **Appetite**: KPI悪化時は**Safemode必須**  
- **Mitigations**: `flags.risk_safemode=true` で Noctus 境界 0.5x、配分 7% 段階へダウン、A/Bで優位戦略へ切替  
- **KPI/Triggers**:  
  - `kpi_max_dd_pct` 7日移動 ≥ `risk_policy.max_drawdown_pct * 0.7`  
  - `kpi_win_rate` 7日移動 ≤ 0.48  
  - `risk_events_total{kind="LOSING_STREAK"}` 増分 > 0（即時）  
- **Runbooks**: §6（取引抑制）/ §8（ロールバック）  
- **Status**: Watching → **自動Safemode**まで設定済

### R-02 流動性低下/スリッページ急騰
- **Category**: 市場/実行 / **Owner**: Ops/Do / **Score**: 12 (**Orange**) / **Appetite**: p90 Slippage ≤ 0.3%  
- **Mitigations**: 分割発注/タイミング最適化、`max_slippage_pct` で自動中断、影響銘柄は一時除外  
- **KPI/Triggers**: `histogram_quantile(0.90, do_slippage_pct_bucket)` > 0.3 for 10m → **Pause検討**  
- **Runbooks**: §9.2 / **Do Contract**: §5.2

### R-03 ブローカー/API 障害
- **Category**: 外部依存 / **Owner**: Ops / **Score**: 15 (**Red**) / **Appetite**: 主要DAG停止時間 ≤ 30m  
- **Mitigations**: リトライ/指数バックオフ、代替経路、`global_trading_pause`、Webhook バッファリング  
- **KPI/Triggers**: `broker_api_errors_total / requests_total` > 0.01 for 10m、`broker_api_latency_seconds` p95 > 2s  
- **Runbooks**: §4/§9, API: `/ops/trading/pause`

### R-04 データ欠損/品質劣化（Plan）
- **Mitigations**: `max_fill_gap` 以内の F/BFill + 欠損フラグ、再取得DAG、データドリフト警告  
- **KPI/Triggers**: 欠損比率 > 1%/日、`KpiSummaryStale` 発火  
- **Links**: `Plan-Layer.md §6`, `Observability.md §10`

### R-06 Idempotency破れ/重複発注
- **Mitigations**: `Idempotency-Key` 必須、`audit_order.json` でハッシュ照合、重複検知で REJECT  
- **KPI/Triggers**: 同一 `correlation_id` で `orders_submitted_total` が 2 以上 → アラート  
- **Links**: `API.md §2`, `Do-Layer-Contract.md §8`

### R-07 リスク境界の誤設定/バイパス
- **Mitigations**: Config 二重承認（PR + King 承認）、Safemode 既定 ON（prod）、起動時に境界を**検証ログ**  
- **KPI/Triggers**: `risk_policy_validation_errors_total` > 0 → Pager、`flags.risk_safemode` が OFF で 24h 継続 → Warning  
- **Links**: `Config-Registry.md §8`, `Vision-Governance.md §5`

### R-08 モデルドリフト/過学習
- **Mitigations**: Walk-Forward、Optuna再学習、Shadow運用10日、段階導入7→30→100%  
- **KPI/Triggers**: `kpi_win_rate` 30日移動が 0.5 を割込、`sigma_mean` 異常（観測不足/過信）  
- **Links**: `ModelCard-Prometheus-PPO.md §10/11`, `Strategy-Lifecycle.md`

### R-09 スキーマドリフト（Plan→Do→Check）
- **Mitigations**: `jsonschema` CI、契約テスト（3パターン：FILLED/PARTIAL/REJECTED）、SemVer 運用  
- **KPI/Triggers**: スキーマ検証失敗数 > 0 → ビルド失敗  
- **Links**: `Do-Layer-Contract.md §12`, `API.md §12`

### R-10 Secrets漏えい/鍵期限切れ
- **Mitigations**: Vault/ENV 専用、90日ローテ、スキャン（静的/PR時）、監査  
- **KPI/Triggers**: 期限 ≤ 7日通知、失敗アクセスの増分 > 0  
- **Links**: `Security-And-Access.md`, `.env.sample`, `Runbooks.md §10`

### R-11 Airflow スケジューラ停止/滞留
- **Mitigations**: HealthCheck監視、再起動Runbook、Backfill指針、pool/並列度の上限設計  
- **KPI/Triggers**: `airflow_dag_runs_total{status="failed"}` 比率 > 5%（5m）、`pdca_check_flow` SLA miss  
- **Links**: `Airflow-DAGs.md §10/12`, `Runbooks.md §9.1`

（…他リスクは要約表のオーナーが担当し、同形式で追記）

---

## 4. アクションの自動化（Flags/Ops）
- **取引抑制**: `flags.global_trading_pause=true` → `/api/v1/ops/trading/pause`（GUI/CLI からも）  
- **Safemode**: `flags.risk_safemode=true`（Noctus 境界 0.5x）  
- **通知先**: Slack `#ops-alerts` / `#risk-duty`、PagerDuty（Severity 連動）  
- **ダッシュボード注釈**: 段階導入/インシデント/ロールバックを Grafana 注釈へ（`Observability.md §6`）

---

## 5. レビュー運用（Cadence）
- **Daily**: 重大アラート/新規リスクの**一次評価**（Ops+Risk）。  
- **Weekly**: Council で**Orange/Red**の進捗レビュー・Owner更新。  
- **Monthly**: 全件見直し、**Appetite/閾値**の適正化、`Release-Notes.md` への反映。  
- **Postmortem**: インシデント24h以内に草案 → 根本原因/再発防止 → 本表へ移す。

---

## 6. 追加テンプレ（New Risk Template）
```md
### R-XX {タイトル}
- **Category**: {市場/実行/データ/…} / **Owner**: {役割} / **Score**: L×I / **Appetite**: {定量 or ルール}
- **Mitigations**: {既存/恒久/短期の対策を箇条書き}
- **KPI/Triggers**: {PromQL/メトリクス/条件 or 手動判定}
- **Runbooks/Links**: {関連手順/設計/契約/ADR}
- **Status**: {Open/Watching/Mitigated/Accepted/Closed}
- **Next Review**: {YYYY-MM-DD}
```

---

## 7. 変更管理（Docs as Code）
- 重要な閾値変更は `Config-Registry.md` と**同一PR**で更新。  
- 恒久対策は `ADRs/` に Decision/Context/Consequences を記録。  
- 関連手順は `Runbooks.md`、監視は `Observability.md` を同期。

---

## 8. 変更履歴（Changelog）
- **2025-08-12**: 初版作成（スコア規約/トップリスク/自動化/テンプレ/運用）


<!-- AUTOGEN:CHANGELOG START -->

### 🛠 Updates since: `2025-08-12 03:36 UTC`

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
- `b2aa77a` 2025-08-14T01:09:50+09:00 — **Update pdca_latency_daily.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_latency_daily.html`
- `38a01da` 2025-08-14T01:06:15+09:00 — **Update pdca_timeline.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_timeline.html`
- `303f8d2` 2025-08-14T01:02:09+09:00 — **Update observability.py** _(by Noctoria)_
  - `noctria_gui/routes/observability.py`
- `206dac2` 2025-08-14T00:21:25+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `c08e345` 2025-08-13T23:37:10+09:00 — **Update init_obs_schema.sql** _(by Noctoria)_
  - `scripts/init_obs_schema.sql`
- `00df80a` 2025-08-13T23:18:49+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `f08d9c2` 2025-08-13T23:12:35+09:00 — **Create init_obs_schema.sql** _(by Noctoria)_
  - `scripts/init_obs_schema.sql`
- `a021461` 2025-08-13T22:07:03+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `d1e0cd2` 2025-08-13T22:01:43+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `435b19e` 2025-08-13T21:57:54+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `82cc0ad` 2025-08-13T16:33:01+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `c42088c` 2025-08-13T16:29:45+09:00 — **Update observability.py** _(by Noctoria)_
  - `noctria_gui/routes/observability.py`
- `5cfbeff` 2025-08-13T16:15:55+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `8c5b055` 2025-08-13T16:11:34+09:00 — **Create pdca_latency_daily.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_latency_daily.html`
- `f8c1e9a` 2025-08-13T16:10:52+09:00 — **Create pdca_timeline.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_timeline.html`
- `3bc104a` 2025-08-13T16:07:38+09:00 — **Create observability.py** _(by Noctoria)_
  - `noctria_gui/routes/observability.py`
- `b1453a0` 2025-08-13T16:03:47+09:00 — **Update order_execution.py** _(by Noctoria)_
  - `src/execution/order_execution.py`
- `9ed85b3` 2025-08-13T15:53:16+09:00 — **Update risk_policy.py** _(by Noctoria)_
  - `src/execution/risk_policy.py`
- `b112ce9` 2025-08-13T15:30:22+09:00 — **Update contracts.py** _(by Noctoria)_
  - `src/plan_data/contracts.py`
- `fba6dda` 2025-08-13T15:24:26+09:00 — **Update risk_gate.py** _(by Noctoria)_
  - `src/execution/risk_gate.py`
- `112e173` 2025-08-13T15:18:00+09:00 — **Create risk_policy.py** _(by Noctoria)_
  - `src/execution/risk_policy.py`
- `99a3122` 2025-08-13T14:53:14+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `9786e16` 2025-08-13T14:49:18+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `3696066` 2025-08-13T14:45:26+09:00 — **Create show_timeline.py** _(by Noctoria)_
  - `src/tools/show_timeline.py`
- `dee8185` 2025-08-13T14:38:49+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `a33f63e` 2025-08-13T14:17:31+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `3fe7a25` 2025-08-13T13:42:41+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `aa30bc6` 2025-08-13T13:33:25+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `7b71201` 2025-08-13T13:30:05+09:00 — **Update path_config.py** _(by Noctoria)_
  - `src/core/path_config.py`
- `8305919` 2025-08-13T13:22:29+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `be7bfa6` 2025-08-13T13:16:51+09:00 — **Create __init__.py** _(by Noctoria)_
  - `src/strategies/__init__.py`
- `7aa58ce` 2025-08-13T13:16:23+09:00 — **Create __init__.py** _(by Noctoria)_
  - `src/e2e/__init__.py`
- `70d8587` 2025-08-13T13:16:11+09:00 — **Create __init__.py** _(by Noctoria)_
  - `src/decision/__init__.py`
- `14a5297` 2025-08-13T13:14:58+09:00 — **Update __init__.py** _(by Noctoria)_
  - `src/__init__.py`
- `e331d07` 2025-08-13T13:12:08+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `4567802` 2025-08-13T13:09:30+09:00 — **Update __init__.py** _(by Noctoria)_
  - `src/__init__.py`
- `4a02589` 2025-08-13T13:06:52+09:00 — **Update decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `b9c0561` 2025-08-13T12:58:07+09:00 — **Update decision_engine.py** _(by Noctoria)_
  - `src/decision/decision_engine.py`
- `7913390` 2025-08-13T12:55:44+09:00 — **Create profile_loader.py** _(by Noctoria)_
  - `src/plan_data/profile_loader.py`
- `e29e4bb` 2025-08-13T12:50:28+09:00 — **Create risk_gate.py** _(by Noctoria)_
  - `src/execution/risk_gate.py`
- `5c617c4` 2025-08-13T12:43:52+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `44bc542` 2025-08-13T11:26:05+09:00 — **Update decision_engine.py** _(by Noctoria)_
  - `src/decision/decision_engine.py`
- `8b7bc76` 2025-08-13T11:24:48+09:00 — **Rename decision_engine.py to decision_engine.py** _(by Noctoria)_
  - `src/decision/decision_engine.py`
- `e70244e` 2025-08-13T11:23:29+09:00 — **Rename trace.py to trace.py** _(by Noctoria)_
  - `src/core/trace.py`
- `7dfab9c` 2025-08-13T11:17:32+09:00 — **Update trace.py** _(by Noctoria)_
  - `src/plan_data/trace.py`
- `735a519` 2025-08-13T11:02:21+09:00 — **Create decision_minidemo.py** _(by Noctoria)_
  - `src/e2e/decision_minidemo.py`
- `e4a9e83` 2025-08-13T10:58:32+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `9c1c5d0` 2025-08-13T10:50:29+09:00 — **Update decision_engine.py** _(by Noctoria)_
  - `src/plan_data/decision_engine.py`
- `31a28ae` 2025-08-13T10:47:02+09:00 — **Update trace.py** _(by Noctoria)_
  - `src/plan_data/trace.py`
- `c7c65fb` 2025-08-13T04:55:43+09:00 — **Update plan_to_all_minidemo.py** _(by Noctoria)_
  - `src/plan_data/plan_to_all_minidemo.py`
- `4ee7b2c` 2025-08-13T04:33:54+09:00 — **Update utils.py** _(by Noctoria)_
  - `src/core/utils.py`
- `7a72c02` 2025-08-13T04:26:01+09:00 — **Update aurus_singularis.py** _(by Noctoria)_
  - `src/strategies/aurus_singularis.py`
- `9738c0b` 2025-08-13T04:18:54+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `668d424` 2025-08-13T04:07:33+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `f06ae54` 2025-08-13T03:05:40+09:00 — **Update plan_to_all_minidemo.py** _(by Noctoria)_
  - `src/plan_data/plan_to_all_minidemo.py`
- `831ff6c` 2025-08-13T02:53:37+09:00 — **Create strategy_adapter.py** _(by Noctoria)_
  - `src/plan_data/strategy_adapter.py`
- `43c5d7a` 2025-08-13T02:53:07+09:00 — **Update trace.py** _(by Noctoria)_
  - `src/plan_data/trace.py`
- `fc92ef5` 2025-08-13T02:50:18+09:00 — **Update analyzer.py** _(by Noctoria)_
  - `src/plan_data/analyzer.py`
- `76795bf` 2025-08-13T02:47:28+09:00 — **Update statistics.py** _(by Noctoria)_
  - `src/plan_data/statistics.py`
- `af4106e` 2025-08-13T02:44:27+09:00 — **Update features.py** _(by Noctoria)_
  - `src/plan_data/features.py`
- `34e7328` 2025-08-13T02:40:33+09:00 — **Update collector.py** _(by Noctoria)_
  - `src/plan_data/collector.py`
- `b80bcf2` 2025-08-13T02:24:16+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `386097b` 2025-08-13T01:53:40+09:00 — **Create ai_adapter.py** _(by Noctoria)_
  - `src/plan_data/ai_adapter.py`
- `881c42c` 2025-08-13T01:52:58+09:00 — **Create observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `04080ca` 2025-08-13T01:52:28+09:00 — **Create trace.py** _(by Noctoria)_
  - `src/plan_data/trace.py`
- `2f52073` 2025-08-13T01:52:00+09:00 — **Create decision_engine.py** _(by Noctoria)_
  - `src/plan_data/decision_engine.py`
- `e40ac8c` 2025-08-13T01:50:14+09:00 — **Create quality_gate.py** _(by Noctoria)_
  - `src/plan_data/quality_gate.py`
- `1de46ad` 2025-08-13T01:49:35+09:00 — **Create contracts.py** _(by Noctoria)_
  - `src/plan_data/contracts.py`

<!-- AUTOGEN:CHANGELOG END -->
