# 🏰 Noctria Kingdom アーキテクチャ概要

**Document Version:** 1.2.6  
**Status:** Working  
**Last Updated:** 2025-08-14 (JST)

> 目的: Noctria の **統治型 PDCA** (Plan / Do / Check / Act)、中央統治 (King / GUI / Airflow)、AI 臣下群、**契約とガードレール**を一望できる形で定義する。  
> 本版は **trace_id E2E 貫通、最小版 DecisionEngine、Observability（timeline / latency 日次）GUI、systemd+Gunicorn 運用、Airflow↔Postgres のネットワーク連携** を反映。

---

## 1. 概要

Noctria Kingdom は、AI による自動売買戦略の **生成 → 実行 → 評価 → 改善** を継続運用する **統治型 PDCA システム**。  
中央統治者 **King Noctria** が最終意思決定を行い、複数の特化型 AI 臣下が助言・分析・実行を担う。  
ワークフローは **Apache Airflow** (DAG) でオーケストレーションし、**FastAPI GUI** で可視化・制御する。

---

## 2. 統治構造 (役割と権限)

### 中央統治者
- **King Noctria** — 王国の全戦略・実行・評価サイクルの最終意思決定者（Two-Person + King 承認の最終ゲート）。

### 臣下 AI（`src/strategies/`）
| 名称 | ファイル/ディレクトリ | 役割 | 主な機能 |
|---|---|---|---|
| **Aurus Singularis** | `src/strategies/Aurus_Singularis.py` | 戦略設計 AI | 市場トレンド解析、戦術策定 |
| **Levia Tempest** | `src/strategies/Levia_Tempest.py` | スキャルピング AI | 高速取引による短期利益獲得 |
| **Noctus Sentinella** | `src/strategies/Noctus_Sentinella.py` | リスク管理 AI | リスク評価、異常検知、Lot 制限 |
| **Prometheus Oracle** | `src/strategies/Prometheus_Oracle.py` | 未来予測 AI | 中長期市場動向の予測 |
| **Veritas** | `src/veritas/` | 戦略生成/最適化 (ML) | 学習・検証・プロファイル管理 |
| **Hermes Cognitor** | `src/hermes/` | 戦略説明 (LLM) | 戦略の自然言語説明、要因分析 |

---

## 3. PDCA サイクル構造

- **Plan 層**: 市場データ収集 → 特徴量生成 → KPI 下地 → 臣下 AI への提案入力  
- **Do 層**: **Noctus Gate** による **境界ガード** → 発注最適化 → 実行/監査  
- **Check 層**: 実績評価 (KPI / アラート / 監査照合)  
- **Act 層**: 再評価 / 再学習 → 段階導入 (7% → 30% → 100%) → Plan へフィードバック  

**昇格基準（例）**: 勝率 +3% 以上（90D MA, ベンチ比）/ 最大 DD ≤ -5%（30D）/ RMSE・MAE 5% 以上改善  
**ロールバック条件（例）**: 勝率 -3% 以上悪化 / 最大 DD ≤ -10% / 重大リスクアラート発火

---

## 4. 中央統治基盤

- **Airflow Orchestrator**: DAG により PDCA を統括  
  - **SLO 例**: DAG 成功率 ≥ 99%、スケジューラ遅延 p95 ≤ 2 分  
  - **冪等性**: 再実行安全（副作用は一意キー制御）
- **FastAPI GUI**: HUD スタイルで PDCA の状態・抑制・段階導入を可視化/操作  
  - **Observability 画面（実装済）**:  
    - `/pdca/timeline` … トレース時系列（`obs_trace_timeline`）  
    - `/pdca/latency/daily` … レイテンシ日次 MV（`obs_latency_daily`）  
    - `POST /pdca/observability/refresh` … 観測ビュー定義と MV 更新
- **運用（要点）**: systemd + Gunicorn（UvicornWorker）  
  - 例: `/etc/default/noctria-gui` … `NOCTRIA_OBS_PG_DSN`・`NOCTRIA_GUI_PORT`  
  - ユニットは **`/bin/sh -lc` 経由で ExecStart**（環境変数展開のため）

---

## 5. アーキテクチャ全体図

```mermaid
graph TD

%% ===== styles =====
classDef gui fill:#eaecff,stroke:#6c6fdb,color:#1f235a;
classDef orch fill:#e9f7ff,stroke:#57a3c7,color:#0d3a4a;
classDef plan fill:#eef7ee,stroke:#66a06a,color:#1f3a22;
classDef ai fill:#fff4e6,stroke:#d9a441,color:#5a3a0a;
classDef do fill:#ffecec,stroke:#d97a7a,color:#5a1f1f;
classDef check fill:#f3f3f3,stroke:#8f8f8f,color:#222;
classDef act fill:#f6ecff,stroke:#a178d1,color:#2e1f3a;
classDef obs fill:#e8f1ff,stroke:#5d8fef,color:#0f2a6a;
classDef todo fill:#f8f0e0,stroke:#ff9f43,color:#4a3000;

subgraph GUI ["Noctria GUI (FastAPI)"]
  ROUTES["routes/*"]:::gui
  TPL["templates/*"]:::gui
end

subgraph ORCH ["Airflow Orchestrator"]
  DAGS["dags/*.py"]:::orch
end

subgraph PLAN ["PLAN (src/plan_data)"]
  COL["collector.py"]:::plan
  FEA["features.py"]:::plan
  ANA["analyzer.py"]:::plan
end

subgraph AIU ["AI underlings (src/strategies & others)"]
  AU["Aurus_Singularis.py"]:::ai
  LE["Levia_Tempest.py"]:::ai
  NO["Noctus_Sentinella.py"]:::ai
  PR["Prometheus_Oracle.py"]:::ai
  VE["veritas/*"]:::ai
  HE["hermes/*"]:::ai
end

DEC["RoyalDecisionEngine (min)"]:::plan
GATE["Noctus Gate (risk_gate)"]:::plan

subgraph DO ["Do (src/execution)"]
  EXE["order_execution.py"]:::do
  OPT["optimized_order_execution.py"]:::do
  GEN["generate_order_json.py"]:::do
  BRK["broker_adapter.py"]:::do
end

subgraph CHECK ["Check (src/check)"]
  EVAL["evaluation.py"]:::check
  MON["challenge_monitor.py"]:::check
end

subgraph ACT ["Act (src/act)"]
  RECHK["pdca_recheck.py"]:::act
  PUSH["pdca_push.py"]:::act
  SUM["pdca_summary.py"]:::act
end

OBS["Observability: obs_* tables/views/mview (trace_id貫通)"]:::obs

GUI --> ORCH
ORCH --> PLAN
PLAN --> AIU
AIU --> DEC
DEC --> GATE
GATE --> DO
DO --> CHECK
CHECK --> ACT
ACT --> PLAN

PLAN -.log.-> OBS
AIU -.log.-> OBS
DEC -.log.-> OBS
DO -.log.-> OBS
CHECK -.log.-> OBS
ACT -.log.-> OBS

OPT --> GEN --> BRK
```

---

## 6. 層別詳細図（別ファイル / `docs/architecture/diagrams/`）

- [PLAN 層 詳細図](diagrams/plan_layer.mmd)  
- [DO 層 詳細図](diagrams/do_layer.mmd)  
- [CHECK 層 詳細図](diagrams/check_layer.mmd)  
- [ACT 層 詳細図](diagrams/act_layer.mmd)

### 6.x コンパクト補足

**PLAN**: 収集→特徴量→分析→AI 入力／`obs_plan_runs`・`obs_infer_calls` 記録（遅延 p95 目標 < 3 分）  
**DO**: Noctus Gate で数量/時間帯/銘柄ガード → 実行／`obs_exec_events`・`obs_alerts`  
**CHECK**: KPI 算出・監査照合 → GUI  
**ACT**: 段階導入・ロールバック・レジストリ反映（基準は §3）

---

## 7. システム境界と契約 (Interfaces & Contracts)

- **契約バージョニング**: SemVer（後方互換は v1.x、破壊変更は v2.0+）  
- **契約テスト**: Consumer-Driven Contract Test（Pact 等）を CI に組込み  
- **API**: `/api/v1`（変更系は **Idempotency-Key** 必須、`If-Match`/ETag 推奨）  
- **Do-Layer Contract（例）**  
  - `order_request`: `symbol`, `intent`, `qty`, `limit_price?`, `sl_tp?`, `sources?`, `trace_id?`, `idempotency_key?`  
  - `exec_result`: 送信/受理/約定/失敗とメタ  
  - `risk_event`: policy, severity, reason, details, trace_id
- **タイムスタンプ**: すべて **UTC ISO-8601**（表示は GUI 側で TZ 変換）  
- **DecisionEngine 設定**: `configs/profiles.yaml`（weights / rollout_percent / min_confidence / combine）

**OrderRequest（JSON 例）**
```json
{
  "symbol": "USDJPY",
  "intent": "LONG",
  "qty": 10000.0,
  "order_type": "MARKET",
  "limit_price": null,
  "sl_tp": {"sl": 154.50, "tp": 155.80},
  "sources": [],
  "trace_id": "20250813-060021-USDJPY-demo-fa3ef5a1",
  "idempotency_key": "demo-unique-key-001"
}
```

---

## 8. 可観測性 & セキュリティ（Guardrails）

- **Observability 実体**  
  - テーブル: `obs_plan_runs` / `obs_infer_calls` / `obs_decisions` / `obs_exec_events` / `obs_alerts`  
  - ビュー: `obs_trace_timeline` / `obs_trace_latency` / **マテビュー**: `obs_latency_daily`  
  - GUI: `/pdca/timeline`, `/pdca/latency/daily`, `POST /pdca/observability/refresh`
- **リスク境界（Noctus Gate）**: Do 層で **強制適用**（越境不可）  
- **Secrets**: ENV / Vault 管理。**Git 混入不可**  
- **Two-Person + King**: `risk_policy`・flags・契約破壊変更は二人承認 + King

**Timeline（参考）**
```
ts (UTC)                  | kind       | action
--------------------------+------------+----------------
2025-08-13 06:00:21+00:00 | PLAN:START |
2025-08-13 06:00:28+00:00 | INFER      | demo-model
2025-08-13 06:00:28+00:00 | DECISION   | BUY
2025-08-13 06:00:28+00:00 | EXEC       | BUY
2025-08-13 06:06:00+00:00 | ALERT      | risk.max_order_qty
```

---

## 9. ランタイム前提・ネットワーク

| 項目 | 値/例 | 備考 |
|---|---|---|
| Postgres（Docker） | コンテナ `pg-noctria` | **ホスト 55432→5432** を公開 |
| DSN（WSL から） | `postgresql://noctria:noctria@127.0.0.1:55432/noctria_db` | `NOCTRIA_OBS_PG_DSN` |
| GUI ポート | `8001` | `NOCTRIA_GUI_PORT` |
| Airflow→PG | `docker network connect airflow_docker_default pg-noctria` | 名前解決: `pg-noctria:5432` |

---

## 10. ディレクトリマップ（抜粋）

```
src/
  plan_data/{collector.py,features.py,statistics.py,analyzer.py,trace.py,observability.py,contracts.py}
  strategies/{Aurus_Singularis.py,Levia_Tempest.py,Noctus_Sentinella.py,Prometheus_Oracle.py}
  execution/{order_execution.py,optimized_order_execution.py,generate_order_json.py,broker_adapter.py,risk_gate.py,risk_policy.py}
  decision/decision_engine.py
  check/{evaluation.py,challenge_monitor.py}
  act/{pdca_recheck.py,pdca_push.py,pdca_summary.py}
  tools/show_timeline.py
airflow_docker/dags/*.py
noctria_gui/{main.py,routes/**,templates/**,static/**}
docs/{architecture,apis,operations,observability,security,qa,models,risks,adrs,howto}/**
```

---

## 11. 時刻・環境規約

- **内部処理**: UTC 固定（表示は GUI で TZ 変換）  
- **環境**: `defaults.yml -> {env}.yml -> flags.yml -> secrets` をマージ  
- **相関 ID**: `trace_id` は `src/plan_data/trace.py` で生成・伝搬（HTTP は `X-Trace-Id`）

---

## 12. 変更履歴

- **2025-08-14**: **v1.2.6**  
  - 臣下 AI のパス表記を現行コード（`src/strategies/Aurus_Singularis.py` など）に整合  
  - Observability GUI（`/pdca/timeline`, `/pdca/latency/daily`）と systemd+Gunicorn 運用の要点を明記  
  - Airflow↔Postgres のネットワーク手順（`docker network connect …`）を要約
- **2025-08-13**: v1.2.5  
  - 詳細図リンク（`docs/architecture/diagrams/*.mmd`）を整備、本文は概要を維持
- **2025-08-13**: v1.2.4  
  - Noctus Gate（`risk_gate.py`）Implemented(min) 表記／Observability と GUI ルート明記  
  - DecisionEngine 設定外部化（`configs/profiles.yaml`）を明記
- **2025-08-13**: v1.2  
  - DecisionEngine（最小版）／`obs_decisions`・`obs_exec_events` 追加／trace_id 貫通／契約方針  
- **2025-08-12**: v1.1 … ガードレール/可観測性/ディレクトリ/時刻規約  
- **2025-08-12**: v1.0 初版

<!-- AUTOGEN:CHANGELOG START -->

### 🛠 Updates since: `2025-08-13 17:35 UTC`

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
<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/architecture/diagrams/*.mmd title=アーキテクチャ図（最新セット） fence=mermaid -->
### アーキテクチャ図（最新セット）

#### `docs/architecture/diagrams/act_layer.mmd`

```mermaid
flowchart TD

%% ====== styles (GitHub-safe) ======
classDef inputs fill:#243447,stroke:#4f86c6,color:#e6f0ff;
classDef act fill:#3a2e4d,stroke:#a78bfa,color:#f3e8ff;
classDef train fill:#2d3a2f,stroke:#76c893,color:#e0ffe8;
classDef outputs fill:#1f3b2d,stroke:#6bbf59,color:#d7fbe8;
classDef gov fill:#2e2e2e,stroke:#b7b7b7,color:#ffffff;
classDef obs fill:#1e2a36,stroke:#5dade2,color:#d6eaf8;
classDef todo fill:#323232,stroke:#ff9f43,color:#ffd8a8;

%% ====== INPUTS ======
subgraph INPUTS ["Upstream inputs"]
  KPI["kpi_summary.json<br/>from CHECK"]
  ECONF["eval_config.json<br/>targets / window / metrics<br/><i>TODO:</i> hypothesis id & test settings"]
  GUIACT["GUI: /pdca/recheck & /pdca/summary<br/>human accept or threshold adjust"]
end

%% ====== ACT layer ======
subgraph ACT_LAYER ["ACT layer (src/act & noctria_gui/routes)"]
  RECHECK["pdca_recheck.py<br/>re-evaluate / param search / A-B compare<br/><i>TODO:</i> full experiment tracking"]
  PUSH["pdca_push.py<br/>adopt & release (Git push / tag)<br/><i>TODO:</i> release bundle signature & SBOM"]
  SUMMARY["pdca_summary.py<br/>period & tag summaries<br/><i>TODO:</i> statistical report & benchmarks"]
  FEEDBACK["feedback_adapter.py<br/>proposals back to PLAN<br/><i>TODO:</i> proposal vs applied contract"]
end

%% ====== Training and retraining ======
subgraph TRAINING ["Training and retraining (Airflow)"]
  TRAIN_DAG["train_* DAG<br/>train & validate<br/><i>TODO:</i> auto-trigger from drift/SLO"]
  REGISTRY["models/registry<br/>version / signature / data fingerprint<br/><i>TODO:</i> enforcement"]
end

%% ====== OUTPUTS ======
subgraph OUTPUTS ["Downstream outputs"]
  PLANUPD["plan_update.json<br/>feature/threshold proposals<br/><i>TODO:</i> schema semver"]
  STRATREL["strategy_release.json<br/>selected version & config<br/><i>TODO:</i> schema semver"]
  DASH["dashboard_feed.json<br/>visualization feed"]
end

%% ====== Governance and operations ======
subgraph GOVERNANCE ["Governance and operations"]
  DAG_ACT["Airflow DAG: pdca_act_flow.py<br/>orchestrate<br/><i>TODO:</i> idempotent per trace_id & branch lock"]
  GUI_ROUTE["GUI: /pdca/summary & /pdca/recheck<br/>approve & review<br/><i>TODO:</i> two-person + king workflow events"]
  APPROVAL["approval_record.json<br/>approvers & timestamps<br/><i>TODO:</i> persistence"]
end

%% ====== Observability taps ======
subgraph OBS ["Observability taps (tables)"]
  OBS_ACT["obs_act_runs<br/>start/end/status/duration/approvers<br/><i>TODO:</i> add trace_id & decision_id"]
  OBS_RECHECK["obs_recheck_jobs<br/>trials/best/p values/CI<br/><i>TODO:</i> add trace_id & decision_id"]
  OBS_ALT["obs_alerts<br/>promotion failed / rollback / policy deviation<br/><i>note:</i> table exists (generic)"]
end

%% ====== Policies and identity ======
CRITERIA["promotion_criteria.yaml<br/>thresholds/period/tests<br/><i>TODO:</i> formalize"]
ROLLBACK["rollback_policy.yaml<br/>rules & kill switch<br/><i>TODO:</i> formalize"]
IDS["ids & versions<br/>trace_id / decision_id / schema_version<br/><i>TODO:</i> enforce across outputs"]

%% ====== FLOWS ======
KPI --> RECHECK
ECONF --> RECHECK
GUIACT --> RECHECK
RECHECK --> SUMMARY
RECHECK --> PUSH
RECHECK -. "train data" .-> TRAIN_DAG
TRAIN_DAG --> REGISTRY
PUSH --> STRATREL
SUMMARY --> DASH
FEEDBACK --> PLANUPD

%% ====== Governance links ======
GUI_ROUTE --> RECHECK
GUI_ROUTE --> PUSH
GUI_ROUTE --> APPROVAL
DAG_ACT --> RECHECK
DAG_ACT --> PUSH

%% ====== Policies links ======
CRITERIA --> RECHECK
ROLLBACK --> PUSH

%% ====== Observability links ======
RECHECK -->|log| OBS_RECHECK
PUSH -->|log| OBS_ACT
SUMMARY -->|log| OBS_ACT
APPROVAL -->|log| OBS_ACT
ROLLBACK -->|alert| OBS_ALT

%% ====== Identity propagation (not implemented) ======
KPI -. trace_id .-> RECHECK
RECHECK -. decision_id .-> PUSH
PUSH -. decision_id .-> STRATREL
SUMMARY -. decision_id .-> DASH
PLANUPD -. trace_id .-> FEEDBACK

%% ====== class bindings ======
class KPI,ECONF,GUIACT inputs;
class RECHECK,PUSH,SUMMARY,FEEDBACK act;
class TRAIN_DAG,REGISTRY train;
class PLANUPD,STRATREL,DASH outputs;
class DAG_ACT,GUI_ROUTE,APPROVAL gov;
class OBS_ACT,OBS_RECHECK,OBS_ALT obs;
class CRITERIA,ROLLBACK,IDS todo;
```

#### `docs/architecture/diagrams/check_layer.mmd`

```mermaid
%% CHECK層 詳細図（実績評価・監視・集計） — updated 2025-08-17
flowchart TD

  %% 入力（Do層からの結果/イベント）
  subgraph INPUTS["上流入力 (from DO)"]
    EXECRES["exec_result.json<br/>（約定/損益/コスト）"]
    RISEVT["risk_event.json<br/>（損失/連敗/異常）"]
    AUDIT["audit_order.json<br/>（完全監査ログ）"]
  end

  %% CHECK層本体
  subgraph CHECK["Check層 (src/check)"]
    MON["challenge_monitor.py<br/>・DD監視/連敗監視<br/>・ルール逸脱検知<br/>・アラート生成"]
    EVAL["evaluation.py<br/>・日次/戦略別KPI<br/>・勝率/最大DD/取引数/平均R"]
    AGG["metrics_aggregator.py（planned）<br/>・期間集計/AI別/シンボル別<br/>・ランキング/タグ別比較"]
    STORE["/data/pdca_logs/**/*.json<br/>・評価/監視/指標の永続化"]
    EXP["prometheus_exporter.py（planned）<br/>・/metrics エクスポート"]
  end

  %% 出力（Act/GUI/Obs）
  subgraph OUTPUTS["下流出力 (to ACT/GUI/Obs)"]
    KPI["kpi_summary.json<br/>（/pdca/summary の主要入力）"]
    ALERT["alert_payload.json<br/>（通知/抑制フラグ付き）"]
  end

  %% 統治/運用/GUI
  subgraph ORCH["統治/運用・可視化"]
    GUISUM["GUI: /pdca/summary"]
    GUISTAT["GUI: /statistics/*<br/>（ranking/scoreboard/compare 等）"]
    OBS["GUI: /observability"]
    DAGCHECK["Airflow DAG: check_flow<br/>（定期評価/閾値判定）"]
    NOTIFY["notifier.py（Slack/メール/Webhook）"]
    ACTLINK["Act/Decision 連携（別図）<br/>※アラートが採用候補になる"]
  end

  %% フロー（処理経路）
  EXECRES --> EVAL
  RISEVT  --> MON
  AUDIT   --> EVAL

  EVAL --> AGG
  EVAL --> STORE
  AGG  --> STORE

  MON --> ALERT --> NOTIFY
  AGG --> KPI
  KPI --> GUISUM
  AGG --> GUISTAT

  %% 可観測性
  MON --> EXP
  EVAL --> EXP
  AGG  --> EXP
  EXP  --> OBS

  %% オーケストレーション
  GUISUM --> DAGCHECK
  DAGCHECK --> EVAL
  DAGCHECK --> MON

  %% Act/Decision 連携の位置づけ（本図では詳細割愛）
  ALERT --> ACTLINK
```

#### `docs/architecture/diagrams/do_layer.mmd`

```mermaid
flowchart TD

%% ====== styles (GitHub-safe) ======
classDef inputs fill:#243447,stroke:#4f86c6,color:#e6f0ff;
classDef do fill:#3d2d2d,stroke:#cc9999,color:#ffcccc;
classDef outputs fill:#1f3b2d,stroke:#6bbf59,color:#d7fbe8;
classDef gov fill:#2e2e2e,stroke:#b7b7b7,color:#ffffff;
classDef obs fill:#1e2a36,stroke:#5dade2,color:#d6eaf8;
classDef todo fill:#323232,stroke:#ff9f43,color:#ffd8a8;

%% ====== INPUTS from PLAN/AI ======
subgraph INPUTS ["Upstream inputs (from PLAN / AI)"]
  REQ["order_request.json<br/>symbol / intent / qty / reasons<br/><b>MUST</b> trace_id; <b>SHOULD</b> idempotency_key"]
  RISKPOL["risk_policy.json<br/>risk caps / lot rules / stops / DD thresholds"]
end

%% ====== DO layer ======
subgraph DO_LAYER ["Do layer (src/execution)"]
  ORDER["order_execution.py<br/>basic place / cancel / replace<br/>state tracking<br/><i>TODO:</i> finite state machine"]
  RISK_GATE["risk_gate.py<br/>final risk & lot filter<br/>enforce policy at send-time<br/><i>status:</i> alerts implemented"]
  OPT["optimized_order_execution.py<br/>slippage & fee aware / split & timing<br/>plugin tactics<br/><i>TODO:</i> strategy plugins"]
  GENJSON["generate_order_json.py<br/>build immutable envelope for audit<br/><i>TODO:</i> HMAC sign snapshot"]
  OUTBOX["outbox store<br/>persist before send / retry-safe<br/><i>TODO:</i> implement outbox pattern"]
  BROKER["broker_adapter.py<br/>external API abstraction (mt5 / ccxt / rest)<br/><i>TODO:</i> capabilities & rate limiter"]
  LOGFILE["/data/execution_logs/*.json<br/>place / fill / failure / retry"]
end

%% ====== OUTPUTS to CHECK / ACT ======
subgraph OUTPUTS ["Downstream outputs (to CHECK / ACT)"]
  EXECRES["exec_result.json<br/>fills / avg price / cost<br/>include trace_id & (ideally) idempotency_key"]
  ALERTSRC["risk_event.json<br/>drawdown / streak / abnormal fill<br/>emitted by gate & recon"]
  AUDIT["audit_order.json<br/>complete reproducibility snapshot"]
end

%% ====== GOVERNANCE / ORCHESTRATION ======
subgraph GOVERNANCE ["Governance and operations"]
  GUI_DO["GUI: /pdca/timeline<br/>+ /trigger (manual ops)"]
  DAG_DO["Airflow DAG: do_layer_flow.py<br/>schedule / retry<br/><i>TODO:</i> service vs DAG boundary"]
end

%% ====== OBSERVABILITY TAPS ======
subgraph OBS ["Observability taps (tables)"]
  OBS_EXEC["obs_exec_events<br/>send status / provider response<br/><b>trace_id implemented</b>"]
  OBS_ALT["obs_alerts<br/>policy blocks / broker issues<br/><b>trace_id implemented</b>"]
  OBS_DO["obs_do_metrics<br/>child_orders / retry_counts<br/><i>TODO:</i> add coverage"]
end

%% ====== AUX: broker hardening ======
subgraph AUX ["Broker hardening"]
  CAPS["capabilities handshake<br/>partial fill / replace / tif / min qty<br/><i>TODO</i>"]
  RLIM["rate limiter & backoff<br/>429 / 5xx handling<br/><i>TODO</i>"]
  RECON["reconciliation<br/>positions & trades match<br/>emit risk_event on mismatch<br/><i>TODO</i>"]
end

%% ====== FLOW ======
REQ --> ORDER
RISKPOL --> RISK_GATE
ORDER --> RISK_GATE
RISK_GATE --> OPT
OPT --> GENJSON
GENJSON --> OUTBOX
OUTBOX --> BROKER
BROKER --> EXECRES
EXECRES --> LOGFILE

%% ====== AUDIT PATHS ======
GENJSON --> AUDIT
ORDER -. audit .-> AUDIT
OPT -. audit .-> AUDIT

%% ====== GOVERNANCE LINKS ======
GUI_DO --> ORDER
DAG_DO --> ORDER

%% ====== DOWNSTREAM LINKS ======
EXECRES --> ALERTSRC

%% ====== OBS LINKS ======
ORDER -->|log| OBS_EXEC
RISK_GATE -->|alert| OBS_ALT
OPT -->|log| OBS_DO
BROKER -->|log| OBS_EXEC
EXECRES -->|log| OBS_EXEC

%% ====== AUX LINKS ======
BROKER --> CAPS
BROKER --> RLIM
BROKER --> RECON
RECON --> ALERTSRC

%% ====== IDENTITY / CORRELATION ======
REQ -. trace_id .-> ORDER
ORDER -. trace_id .-> RISK_GATE
RISK_GATE -. trace_id .-> OPT
OPT -. trace_id .-> GENJSON
GENJSON -. trace_id .-> OUTBOX
OUTBOX -. trace_id .-> BROKER
BROKER -. trace_id .-> EXECRES
EXECRES -. trace_id .-> AUDIT

%% ====== IDEMPOTENCY ======
GENJSON -. idempotency_key .-> OUTBOX
OUTBOX -. idempotency_key .-> BROKER
EXECRES -. idempotency_key .-> AUDIT

%% ====== class bindings ======
class REQ,RISKPOL inputs;
class ORDER,RISK_GATE,OPT,GENJSON,OUTBOX,BROKER,LOGFILE do;
class EXECRES,ALERTSRC,AUDIT outputs;
class GUI_DO,DAG_DO gov;
class OBS_EXEC,OBS_ALT,OBS_DO obs;
class CAPS,RLIM,RECON gov;
```

#### `docs/architecture/diagrams/plan_layer.mmd`

```mermaid
flowchart TD

%% ====== styles (GitHub-safe) ======
classDef plan fill:#262e44,stroke:#47617a,color:#d8e0f7;
classDef ai fill:#2f3136,stroke:#a97e2c,color:#ffe476;
classDef do fill:#3d2d2d,stroke:#cc9999,color:#ffcccc;
classDef todo fill:#323232,stroke:#ff9f43,color:#ffd8a8;
classDef obs fill:#1e2a36,stroke:#5dade2,color:#d6eaf8;
classDef demo fill:#202020,stroke:#8a8a8a,color:#eaeaea;

%% ====== PLAN layer ======
subgraph PLAN ["PLAN layer (src/plan_data)"]
  COLLECT["collector.py<br/>market data collection"]:::plan
  FEATURES["features.py<br/>feature engineering"]:::plan
  FEATDF["FeatureBundle output<br/>(df + context)<br/>v1.0"]:::plan
  ANALYZER["analyzer.py<br/>factor extraction"]:::plan
  STATS["statistics.py<br/>KPI aggregation"]:::plan
  ADAPTER["strategy_adapter.py<br/>propose_with_logging<br/>logs obs_infer_calls"]:::plan
end

%% ====== AI underlings ======
subgraph AI_UNDERLINGS ["AI underlings (src/strategies)"]
  AURUS["Aurus<br/>propose()"]:::ai
  LEVIA["Levia<br/>propose()"]:::ai
  PROM["Prometheus<br/>predict_future()"]:::ai
  VERITAS["Veritas<br/>propose()"]:::ai
  HERMES["Hermes<br/>LLM explain (non-exec)"]:::ai
end

%% ====== Decision & Risk ======
DECISION["DecisionEngine (min)<br/>integrate & log<br/>(IMPLEMENTED)"]:::plan
NOCTUSGATE["Noctus Gate<br/>mandatory risk & lot filter<br/>(TODO)"]:::todo
QUALITY["DataQualityGate<br/>missing_ratio / data_lag → SCALE/FLAT<br/>(TODO)"]:::todo
PROFILES["profiles.yaml<br/>weights & rollout 7->30->100%<br/>(TODO)"]:::todo

%% ====== Contracts ======
CONTRACTS["Contracts<br/>FeatureBundle & StrategyProposal v1.0<br/>OrderRequest (TBD)"]:::todo
TRACEID["Correlation ID trace_id<br/>PLAN/AI/Decision/Exec implemented"]:::plan

%% ====== Do layer (handoff) ======
subgraph DO_LAYER ["Do layer (handoff)"]
  ORDER["order_execution.py<br/>execution API (dummy ok)"]:::do
end

%% ====== Demo & tests ======
subgraph DEMO ["Demo and tests"]
  DECISION_MINI["e2e/decision_minidemo.py<br/>E2E (IMPLEMENTED)"]:::demo
  TEST_E2E["tests/test_trace_decision_e2e.py<br/>integration (IMPLEMENTED)"]:::demo
end

%% ====== Observability taps ======
subgraph OBS ["Observability taps (tables)"]
  OBS_PLAN["obs_plan_runs<br/>collector/features/statistics/analyzer<br/>trace_id present"]:::obs
  OBS_INFER["obs_infer_calls<br/>AI propose/predict latency<br/>trace_id present"]:::obs
  OBS_DEC["obs_decisions<br/>decision metrics & reasons<br/>trace_id present (NEW)"]:::obs
  OBS_EXEC["obs_exec_events<br/>send status / provider response<br/>trace_id present (NEW)"]:::obs
  OBS_ALT["obs_alerts<br/>quality or risk alerts<br/>(TODO)"]:::obs
end

%% ====== PLAN flow ======
COLLECT --> FEATURES --> STATS
FEATURES --> FEATDF
FEATDF --> ANALYZER
ANALYZER --> HERMES
FEATDF --> ADAPTER
ADAPTER --> AURUS
ADAPTER --> LEVIA
ADAPTER --> PROM
ADAPTER --> VERITAS

%% ====== Contracts wiring ======
FEATDF -. "uses" .-> CONTRACTS
ADAPTER -. "uses" .-> CONTRACTS
AURUS -. "returns" .-> CONTRACTS
LEVIA -. "returns" .-> CONTRACTS
PROM  -. "returns" .-> CONTRACTS
VERITAS -. "returns" .-> CONTRACTS

%% ====== Decision integration path ======
FEATDF --> QUALITY
QUALITY --> DECISION
AURUS --> DECISION
LEVIA --> DECISION
PROM  --> DECISION
VERITAS --> DECISION
PROFILES -. "config" .-> DECISION
DECISION --> NOCTUSGATE
NOCTUSGATE --> ORDER

%% ====== Demo edges ======
DECISION_MINI --> FEATDF
DECISION_MINI --> DECISION
DECISION_MINI --> ORDER
TEST_E2E -. "psql counts by trace_id" .-> OBS_PLAN
TEST_E2E -.-> OBS_INFER
TEST_E2E -.-> OBS_DEC
TEST_E2E -.-> OBS_EXEC

%% ====== Observability wiring ======
COLLECT  -->|log| OBS_PLAN
FEATURES -->|log| OBS_PLAN
STATS    -->|log| OBS_PLAN
ANALYZER -->|log| OBS_PLAN
AURUS    -->|log| OBS_INFER
LEVIA    -->|log| OBS_INFER
PROM     -->|log| OBS_INFER
VERITAS  -->|log| OBS_INFER
DECISION -->|log| OBS_DEC
ORDER    -->|log| OBS_EXEC
NOCTUSGATE -->|alert| OBS_ALT

%% ====== trace_id notes ======
FEATDF -. "trace_id (PLAN & AI implemented)" .-> AURUS
FEATDF -. "trace_id (PLAN & AI implemented)" .-> LEVIA
FEATDF -. "trace_id (PLAN & AI implemented)" .-> PROM
FEATDF -. "trace_id (PLAN & AI implemented)" .-> VERITAS
DECISION -. "trace_id (P->D->Exec implemented)" .-> ORDER

%% ====== class bindings ======
class COLLECT,FEATURES,FEATDF,ANALYZER,STATS,ADAPTER plan;
class AURUS,LEVIA,PROM,VERITAS,HERMES ai;
class ORDER do;
class DECISION plan;
class NOCTUSGATE,QUALITY,PROFILES,CONTRACTS todo;
class TRACEID plan;
class OBS_PLAN,OBS_INFER,OBS_DEC,OBS_EXEC,OBS_ALT obs;
class DECISION_MINI,TEST_E2E demo;
```
<!-- AUTODOC:END -->

<!-- AUTODOC:BEGIN mode=git_log path_globs=src/**/*.py title=コードベース更新履歴（最近30） limit=30 since=2025-08-01 -->
### コードベース更新履歴（最近30）

- **6a2294c** 2025-08-20T02:31:07+09:00 — Update pdca_summary_service.py (by Noctoria)
  - `src/plan_data/pdca_summary_service.py`
- **0a246cf** 2025-08-19T02:37:10+09:00 — Update pdca_summary_service.py (by Noctoria)
  - `src/plan_data/pdca_summary_service.py`
- **73b1b0d** 2025-08-18T03:37:41+09:00 — Update pdca_summary_service.py (by Noctoria)
  - `src/plan_data/pdca_summary_service.py`
- **3c389b0** 2025-08-17T21:58:56+09:00 — Create decision_hooks.py (by Noctoria)
  - `src/core/decision_hooks.py`
- **a19193a** 2025-08-16T05:25:12+09:00 — Update airflow_client.py (by Noctoria)
  - `src/core/airflow_client.py`
- **b96eae7** 2025-08-16T05:16:53+09:00 — Update git_utils.py (by Noctoria)
  - `src/core/git_utils.py`
- **e25e60a** 2025-08-16T04:11:29+09:00 — Update decision_registry.py (by Noctoria)
  - `src/core/decision_registry.py`
- **b2a650a** 2025-08-16T04:08:59+09:00 — Create git_utils.py (by Noctoria)
  - `src/core/git_utils.py`
- **a39c7db** 2025-08-15T04:14:15+09:00 — Update observability.py (by Noctoria)
  - `src/plan_data/observability.py`
- **09a3e13** 2025-08-15T03:51:14+09:00 — Update Aurus_Singularis.py (by Noctoria)
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- **4b38d3b** 2025-08-15T01:48:52+09:00 — Update path_config.py (by Noctoria)
  - `src/core/path_config.py`
- **00fc537** 2025-08-15T01:44:12+09:00 — Create kpi_minidemo.py (by Noctoria)
  - `src/plan_data/kpi_minidemo.py`
- **daa5865** 2025-08-15T01:37:54+09:00 — Update Aurus_Singularis.py (by Noctoria)
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- **5e52eca** 2025-08-15T01:35:28+09:00 — Update Aurus_Singularis.py (by Noctoria)
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- **e320246** 2025-08-15T01:34:39+09:00 — Update Aurus_Singularis.py (by Noctoria)
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- **de39f94** 2025-08-15T01:33:29+09:00 — Create Aurus_Singularis.py (by Noctoria)
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- **4d7dd70** 2025-08-15T00:28:18+09:00 — Update act_service.py (by Noctoria)
  - `src/core/act_service.py`
- **1d38c3c** 2025-08-14T22:21:33+09:00 — Create policy_engine.py (by Noctoria)
  - `src/core/policy_engine.py`
- **dcdd7f4** 2025-08-14T22:15:59+09:00 — Update airflow_client.py (by Noctoria)
  - `src/core/airflow_client.py`
- **e0b9eaa** 2025-08-14T21:53:00+09:00 — Update pdca_summary_service.py (by Noctoria)
  - `src/plan_data/pdca_summary_service.py`
- **d0df823** 2025-08-14T21:18:54+09:00 — Update decision_registry.py (by Noctoria)
  - `src/core/decision_registry.py`
- **b557920** 2025-08-14T21:03:59+09:00 — Update strategy_evaluator.py (by Noctoria)
  - `src/core/strategy_evaluator.py`
- **0c7a12f** 2025-08-14T21:00:00+09:00 — Create decision_registry.py (by Noctoria)
  - `src/core/decision_registry.py`
- **307da2d** 2025-08-14T20:49:15+09:00 — Create act_service.py (by Noctoria)
  - `src/core/act_service.py`
- **46d639d** 2025-08-14T20:17:49+09:00 — Update strategy_evaluator.py (by Noctoria)
  - `src/core/strategy_evaluator.py`
- **2b51ef9** 2025-08-14T04:27:11+09:00 — Create pdca_summary_service.py (by Noctoria)
  - `src/plan_data/pdca_summary_service.py`
- **d8e0d6e** 2025-08-14T04:12:02+09:00 — Create airflow_client.py (by Noctoria)
  - `src/core/airflow_client.py`
- **206dac2** 2025-08-14T00:21:25+09:00 — Update observability.py (by Noctoria)
  - `src/plan_data/observability.py`
- **435b19e** 2025-08-13T21:57:54+09:00 — Update observability.py (by Noctoria)
  - `src/plan_data/observability.py`
- **b1453a0** 2025-08-13T16:03:47+09:00 — Update order_execution.py (by Noctoria)
  - `src/execution/order_execution.py`
<!-- AUTODOC:END -->
