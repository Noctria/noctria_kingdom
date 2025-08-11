# 🏰 Noctria Kingdom アーキテクチャ概要

---

## 1. 概要
Noctria Kingdom プロジェクトは、AIによる自動売買戦略の生成・実行・再評価を行う **統治型PDCAシステム** です。  
中央統治者 **King Noctria** が全ての最終意思決定を行い、複数の特化型AI臣下が助言・分析・実行を担います。

システムは **Apache Airflow** によるDAGワークフローで運用され、**FastAPIベースのGUI** で可視化・制御されます。

---

## 2. 統治構造（役割と権限）

### 中央統治者
- **King Noctria**  
  王国の全戦略・実行・評価サイクルの最終意思決定者。

### 臣下AI（src/strategies/）
| 名称 | ファイル | 役割 | 主な機能 |
|------|----------|------|----------|
| **Aurus Singularis** | `aurus_singularis.py` | 戦略設計AI | 市場トレンド解析、戦術策定 |
| **Levia Tempest** | `levia_tempest.py` | スキャルピングAI | 高速取引による短期利益獲得 |
| **Noctus Sentinella** | `noctus_sentinella.py` | リスク管理AI | リスク評価、異常検知、lot制限 |
| **Prometheus Oracle** | `prometheus_oracle.py` | 未来予測AI | 中長期市場動向の予測 |
| **Veritas Machina** | `veritas_machina.py` | 戦略生成AI（ML） | 戦略の機械学習生成 |
| **Hermes Cognitor** | `hermes_cognitor.py` | 戦略説明AI（LLM） | 戦略の自然言語説明、要因分析 |

---

## 3. PDCAサイクル構造

- **Plan層**: 市場データ収集、特徴量生成、戦略提案（臣下AI）
- **Do層**: 発注実行、リスク制御、結果記録
- **Check層**: 実績評価、リスク監視
- **Act層**: 再評価、改善戦略の適用（Plan層へフィードバック）

---

## 4. 中央統治基盤
- **Airflow Orchestrator**  
  各層のワークフロー（DAG）を管理し、PDCAループ全体を統括
- **FastAPI GUI**  
  HUDスタイルの管理画面でPDCA全体の可視化・手動制御を実現

---

## 5. アーキテクチャ全体図

```mermaid
flowchart TD

  %% --- GUI ---
  subgraph GUI["🎛️ Noctria GUI (FastAPI)"]
    ROUTES["routes/*.py<br>戦略比較/PDCA/AI一覧"]
    TEMPLATES["templates/*.html<br>HUDダッシュボード"]
  end

  %% --- Airflow ---
  subgraph ORCH["🪄 Airflow Orchestrator"]
    DAGS["/airflow_docker/dags/*.py<br>PDCA/戦略生成/評価DAG"]
  end

  %% --- PLAN層 ---
  subgraph PLAN["🗺️ PLAN層"]
    COLLECT["collector.py<br>市場データ収集"]
    FEATURES["features.py<br>特徴量生成"]
    STATS["statistics.py<br>KPI算出"]
    ANALYZER["analyzer.py<br>要因抽出"]
  end

  %% --- AI臣下 ---
  subgraph AI["🤖 臣下AI (src/strategies/)"]
    AURUS["aurus_singularis.py<br>総合分析"]
    LEVIA["levia_tempest.py<br>スキャルピング"]
    NOCTUS["noctus_sentinella.py<br>リスク管理"]
    PROM["prometheus_oracle.py<br>未来予測"]
    VERITAS["veritas_machina.py<br>ML戦略生成"]
    HERMES["hermes_cognitor.py<br>LLM戦略説明"]
  end

  %% --- DO層 ---
  subgraph DO["⚔️ Do層"]
    ORDER["order_execution.py<br>発注API"]
    OPTORDER["optimized_order_execution.py<br>最適化発注"]
    GENORDER["generate_order_json.py<br>発注内容JSON化"]
  end

  %% --- CHECK層 ---
  subgraph CHECK["🔍 Check層"]
    MON["challenge_monitor.py<br>損失監視"]
    EVAL["evaluation.py<br>実績評価"]
    LOGS["pdca_logs/*.json<br>結果記録"]
  end

  %% --- ACT層 ---
  subgraph ACT["♻️ Act層"]
    RECHECK["pdca_recheck.py<br>再評価"]
    PUSH["pdca_push.py<br>戦略採用"]
    SUMMARY["pdca_summary.py<br>集計/ダッシュボード"]
  end

  %% --- Connections ---
  GUI --> ORCH
  ORCH --> PLAN
  PLAN --> AI
  AI --> DO
  DO --> CHECK
  CHECK --> ACT
  ACT --> PLAN

  %% Internal flows
  COLLECT --> FEATURES --> STATS --> ANALYZER
  STATS --> AURUS
  STATS --> LEVIA
  STATS --> NOCTUS
  STATS --> PROM
  STATS --> VERITAS
  ANALYZER --> HERMES

## 6. 層別詳細図

- [🗺️ PLAN層 詳細図](diagrams/plan_layer.mmd)
- [⚔️ DO層 詳細図](diagrams/do_layer.mmd)
- [🔍 CHECK層 詳細図](diagrams/check_layer.mmd)
- [♻️ ACT層 詳細図](diagrams/act_layer.mmd)
```

> 各 `.mmd` は Mermaid Live Editor または mermaid-cli で SVG/PNG 化して利用できます。
