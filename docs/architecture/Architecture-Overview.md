# 🏰 Noctria Kingdom アーキテクチャ概要

**Document Version:** 1.2.7  
**Status:** Working  
**Last Updated:** 2025-08-23 (JST)

> 目的: Noctria の **統治型 PDCA** (Plan / Do / Check / Act)、中央統治 (King / GUI / Airflow)、AI 臣下群、**契約とガードレール**を一望できる形で定義する。  
> 参照: 設計の単一索引は `docs/architecture/PDCA-Spec.md`。

---

## 1. 概要

Noctria Kingdom は、AI による自動売買戦略の **生成 → 実行 → 評価 → 改善** を継続運用する **統治型 PDCA システム**。  
中央統治者 **King Noctria** が最終意思決定を行い、複数の特化型 AI 臣下が助言・分析・実行を担う。  
ワークフローは **Apache Airflow** (DAG) によりオーケストレーションし、**FastAPI GUI** で可視化・制御する。

---

## 2. 統治構造 (役割と権限)

### 中央統治者
- **King Noctria** — 戦略・実行・評価サイクルの最終意思決定者（Two-Person + King 承認の最終ゲート）。

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

- **Airflow Orchestrator**: DAG により PDCA を統括（SLO 例: 成功率 ≥ 99%、スケジューラ遅延 p95 ≤ 2 分）。  
- **FastAPI GUI**: HUD スタイルで PDCA の状態・抑制・段階導入を可視化/操作。  
  - `/pdca/timeline`（`obs_trace_timeline`）  
  - `/pdca/latency/daily`（`obs_latency_daily`）  
  - `POST /pdca/observability/refresh`
- **運用**: systemd + Gunicorn（UvicornWorker）。  
  - 例: `/etc/default/noctria-gui` … `NOCTRIA_OBS_PG_DSN`・`NOCTRIA_GUI_PORT`  
  - ExecStart は **`/bin/sh -lc`** 経由で環境変数展開。

---

## 5. アーキテクチャ全体図

```mermaid
graph TD
classDef gui fill:#eaecff,stroke:#6c6fdb,color:#1f235a;
classDef orch fill:#e9f7ff,stroke:#57a3c7,color:#0d3a4a;
classDef plan fill:#eef7ee,stroke:#66a06a,color:#1f3a22;
classDef ai fill:#fff4e6,stroke:#d9a441,color:#5a3a0a;
classDef do fill:#ffecec,stroke:#d97a7a,color:#5a1f1f;
classDef check fill:#f3f3f3,stroke:#8f8f8f,color:#222;
classDef act fill:#f6ecff,stroke:#a178d1,color:#2e1f3a;
classDef obs fill:#e8f1ff,stroke:#5d8fef,color:#0f2a6a;

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

GUI --> ORCH --> PLAN --> AIU --> DEC --> GATE --> DO --> CHECK --> ACT --> PLAN
PLAN -.log.-> OBS
AIU -.log.-> OBS
DEC -.log.-> OBS
DO  -.log.-> OBS
CHECK -.log.-> OBS
ACT -.log.-> OBS

OPT --> GEN --> BRK
