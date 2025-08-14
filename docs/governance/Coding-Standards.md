# 🗺 Roadmap & OKRs — Noctria Kingdom

**Document Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Planning Window:** 2025 Q3–2026 Q1  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の**中期ロードマップ**と**OKR（Objectives & Key Results）**を一元管理し、PDCA を継続的に前進させる。  
> 参照：`../governance/Vision-Governance.md` / `../architecture/Architecture-Overview.md` / `../operations/Runbooks.md` / `../operations/Airflow-DAGs.md` / `../operations/Config-Registry.md` / `../observability/Observability.md` / `../apis/Do-Layer-Contract.md` / `../risks/Risk-Register.md` / `./Release-Notes.md`

---

## 1) スコープ & 原則
- スコープ：**機能/運用/セキュリティ/モデル/可観測性**に跨るプロジェクト横断の優先順位。  
- 原則：
  1. **Guardrails First** — `Non-Negotiables`（Noctus 境界/監査/Secrets）は期限より優先。  
  2. **Measure What Matters** — すべての KR は **観測可能メトリクス**に紐づける。  
  3. **Docs-as-Code** — 変更は**同一PRで文書更新**（`Release-Notes.md` に反映）。  
  4. **Small Safe Steps** — 段階導入（7%→30%→100%）を標準運用。

---

## 2) 時間軸・リリース計画（暫定）
- **2025.08 “Foundation”**：初版ドキュメント/契約/標準（リリース済）  
- **2025.09 “Stability”**：運用耐性/監視強化、Do層 QoS 安定  
- **2025.10 “Throughput”**：発注最適化v2、Airflow キュー分離  
- **2025.12 “Governance+”**：Two-Person/監査の自動化、セキュアリリースゲート  
- **2026.01 “Alpha Models”**：Prometheus 1.x 強化、Veritas 自動探索MVP

```mermaid
gantt
    title Noctria Roadmap (2025 Q3–2026 Q1)
    dateFormat  YYYY-MM-DD
    section Ops & Orchestration
    Stability (QoS,pools)        :done,   a1, 2025-08-12, 2025-09-30
    Throughput (queues,split v2) :active, a2, 2025-10-01, 2025-10-31
    Governance+ (gate)           :        a3, 2025-11-01, 2025-12-20
    section Models
    Prometheus 1.x hardening     :active, m1, 2025-09-01, 2025-10-31
    Veritas AutoSearch MVP       :        m2, 2025-11-15, 2026-01-31
    section Security & Access
    2FA/OIDC roll-out            :done,   s1, 2025-08-12, 2025-09-15
    Secrets rotation automation  :        s2, 2025-11-01, 2025-12-15
    section Observability
    Canary annotations automate  :active, o1, 2025-09-10, 2025-10-10
    KPI schema versioning        :        o2, 2025-10-15, 2025-11-15
```

---

## 3) 戦略テーマ（Pillars）
1. **Reliability & Safety** — 失敗を早く検知し安全に止める  
2. **Execution Performance** — Do 層のレイテンシとスリッページ最適化  
3. **Model Excellence** — 再現性と優位性の持続（WFO/シャドー/段階導入）  
4. **Security & Governance** — 最小権限・監査・Two-Person Rule の自動化  
5. **Dev Velocity** — テスト/CI と構成管理の摩擦低減

---

## 4) OKRs（2025 Q3–Q4 / 2026 Q1）
> スコア評価は **0.0–1.0**。`Owner` はロール名、計測は `Observability.md` のメトリクスを正。

### O-1 Reliability & Safety（Owner: Ops + Risk）
- **KR1.1**：`airflow_dag_success_rate`（月次）≥ **99.2%** を 2 か月連続で達成  
- **KR1.2**：重大アラートから**一次反応 ≤ 5分 (p95)** を 30日継続  
- **KR1.3**：`risk_policy` 越境による **実発注ゼロ**（0件）  
- **KR1.4**：`KpiSummaryStale` アラート **0 件/週**（4週平均）

### O-2 Execution Performance（Owner: Do）
- **KR2.1**：`do_order_latency_seconds` **p95 ≤ 0.40s**（prod, 平日日中, 14日連続）  
- **KR2.2**：`do_slippage_pct` **p90 ≤ 0.30%** を 4 週連続達成（対象シンボル）  
- **KR2.3**：`broker_api_errors_total / requests_total ≤ 1%`（10m 窓、月次平均）

### O-3 Model Excellence（Owner: Models + Risk）
- **KR3.1**：Prometheus 1.x（stg シャドー）で **Sharpe_adj +5%**（対 2025.08 基準）  
- **KR3.2**：本番カナリア中（7%→30%）の **MaxDD ≤ 8%**（Safemode ON）  
- **KR3.3**：`sigma_mean`の異常監視導入（しきい値逸脱**自動アラート**稼働）

### O-4 Security & Governance（Owner: Sec + King）
- **KR4.1**：**Secrets in repo = 0**（gitleaks/CI 100% パス）  
- **KR4.2**：`Two-Person Gate` を `risk_policy/flags/API/Do-Contract` に適用（**4/4 完了**）  
- **KR4.3**：Secrets ローテ **90日**の**自動通知/運用**が稼働（prod）

### O-5 Dev Velocity（Owner: Arch + Ops）
- **KR5.1**：PR から stg デプロイまでの **リードタイム中央値 ≤ 2h**  
- **KR5.2**：E2E スモーク（stg）**合格率 ≥ 95%**（直近30日）  
- **KR5.3**：契約/スキーマ破壊変更は **0 件**（`jsonschema` CI で検出ゼロ）

---

## 5) マイルストーン（Deliverables）
| 期限 | マイルストーン | 受け入れ基準（DoD） | Owner |
|---|---|---|---|
| 2025-09-30 | **Stability 完了** | Pools/Queues 設計、SLAダッシュ、Runbook改訂、KR1.1初達成 | Ops |
| 2025-10-31 | **Throughput 完了** | 発注最適化v2、p95≤0.40s達成、スリッページp90≤0.30% | Do |
| 2025-12-20 | **Governance+ 完了** | Two-Person Gate自動化、監査WORM/注釈連携 | Sec/Arch |
| 2026-01-31 | **Alpha Models 完了** | Veritas MVP、Prometheus 1.x Gate通過、段階導入30% | Models |

---

## 6) 依存関係（Cross-Team / Docs）
- **Runbooks**：抑制度/ロールバック/バックフィル手順の改訂必須（各変更と同一PR）  
- **Config-Registry**：`flags/risk_policy/observability.alerts` の差分管理  
- **Observability**：Rules/ダッシュボード/注釈 API（KR の計測ソース）  
- **Do-Layer-Contract**：最小互換での拡張（Breaking は `/v2` 案で ADR 起票）

---

## 7) リスク & 対応（抜粋）
| リスク | 影響 | 緩和策 | 出口条件 |
|---|---|---|---|
| ブローカー障害長期化 | 発注停止/機会損失 | 代替経路/レート制限緩和/抑制 | Error rate ≤1% を7日維持 |
| スキーマドリフト | 連携失敗 | `jsonschema` CI/契約テスト | 連続 30日 破壊ゼロ |
| モデル優位性劣化 | KPI 低下 | シャドー10日/段階導入/再学習 | G3/G4 Gate を再達成 |

> 詳細は `../risks/Risk-Register.md`（R-02/R-03/R-09/R-08）を参照。

---

## 8) 測定 & データソース（例）
| KR | メトリクス/クエリ | 集計粒度 | 出力先 |
|---|---|---|---|
| KR1.1 | `airflow_dag_runs_total{status}` → 成功率 | 日/週/月 | Grafana: Airflow Board |
| KR2.1 | `histogram_quantile(0.95, do_order_latency_seconds_bucket)` | 5分 | Grafana: Do QoS |
| KR2.2 | `histogram_quantile(0.90, do_slippage_pct_bucket)` | 10分 | Grafana: Do QoS |
| KR3.1 | `kpi_sharpe_adj{env="stg"}` | 1日 | PDCA Summary |
| KR4.1 | gitleaks CI 結果（0件） | PR毎 | GitHub Checks |
| KR5.1 | CI timestamps（PR→Deploy） | PR毎 | Pipeline Board |

---

## 9) ガバナンス & カデンス
- **Weekly Council**：OKR 進捗/リスク/ブロッカーのレビュー（30分）  
- **Monthly Review**：スコア暫定評価、優先順位の再配置、`Release-Notes.md` 更新  
- **Quarter Close**：スコア確定（0.0–1.0）、次期 OKR 起案、ADR 必要分の確定

---

## 10) 変更管理（運用）
- 変更は**同一PR**で：コード＋Docs（本書/Runbooks/Config/Observability/API/Contract）。  
- 破壊的変更は **ADR** 必須（`adrs/`）、`Release-Notes.md` の **Breaking** に記載。  
- マイルストーン達成時は `Release-Notes.md` に**リリース名**と**要点**を追記。

---

## 11) スコアリング規約（OKR Rubric）
- **0.0** 未着手、**0.3** 部分達成、**0.7** ほぼ達成、**1.0** 完全達成（定量条件クリア）  
- 途中で条件を**緩めない**（緩和は別 KR として再定義）  
- 計測不能な KR は**無効**。必ずメトリクス or 監査可能イベントに紐づける。

---

## 12) テンプレ（OKR エントリ）
```md
### O-x {Objective（定性的な方向）}
- KR{x.1}: {定量条件/閾値/期間} — Owner: {Role}
- KR{x.2}: ...
- 計測: {メトリクス/クエリ/出力先}
- リスク: {主要リスクと緩和策リンク}
```

---

## 13) 変更履歴（Changelog）
- **2025-08-12**: 初版作成（テーマ/OKR/ガント/測定/ガバナンス/テンプレ）


<!-- AUTOGEN:CHANGELOG START -->

### 🛠 Updates since: `2025-08-12 07:12 UTC`

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
