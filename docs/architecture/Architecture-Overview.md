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
