# 🏰 Noctria Kingdom アーキテクチャ概要

---

## 1. 概要
Noctria Kingdom プロジェクトは、AIによる自動売買戦略の生成・実行・再評価を行う**統治型PDCAシステム**です。  
中央統治者 **King Noctria** が全ての最終意思決定を行い、複数の特化型AI臣下が助言・分析・実行を担います。

システムは Apache Airflow によるDAGワークフローで運用され、FastAPIベースのGUIで可視化・制御されます。

---

## 2. 統治構造（役割と権限）

### 中央統治者
- **King Noctria**  
  王国の全戦略・実行・評価サイクルの最終意思決定者。

### 臣下AI
| 名称 | 役割 | 主な機能 |
|------|------|----------|
| **Aurus Singularis** | 戦略設計AI | 市場トレンド解析、戦術策定 |
| **Levia Tempest** | スキャルピングAI | 高速取引による短期利益獲得 |
| **Noctus Sentinella** | リスク管理AI | リスク評価、異常検知、lot制限 |
| **Prometheus Oracle** | 未来予測AI | 中長期市場動向の予測 |
| **Veritas Machina** | 戦略生成AI（ML） | 戦略の機械学習生成 |
| **Hermes Cognitor** | 戦略説明AI（LLM） | 戦略の自然言語説明、要因分析 |

---

## 3. PDCAサイクル構造

- **Plan層**: 市場データ収集、特徴量生成、戦略提案
- **Do層**: 発注実行、リスク制御、結果記録
- **Check層**: 実績評価、リスク監視
- **Act層**: 再評価、改善戦略の適用

---

## 4. アーキテクチャ全体図

```mermaid
flowchart TD
  %% --- Plan層 ---
  subgraph PLAN["🗺️ PLAN層（collector→features→analyzer/statistics）"]
    COLLECT["PlanDataCollector<br>市場データ収集"]
    FEATENG["FeatureEngineer<br>特徴量生成"]
    FEATDF["特徴量DataFrame/Dict出力"]
    ANALYZER["PlanAnalyzer<br>要因抽出/ラベル"]
  end

  %% --- AI臣下たち ---
  subgraph AI_UNDERLINGS["🤖 臣下AI群（src/strategies/）"]
    AURUS["🎯 Aurus<br>総合分析<br><b>propose()</b>"]
    LEVIA["⚡ Levia<br>スキャルピング<br><b>propose()</b>"]
    NOCTUS["🛡️ Noctus<br>リスク/ロット判定<br><b>calculate_lot_and_risk()</b>"]
    PROMETHEUS["🔮 Prometheus<br>未来予測<br><b>predict_future()</b>"]
    HERMES["🦉 Hermes<br>LLM説明<br><b>propose()</b>"]
    VERITAS["🧠 Veritas<br>戦略提案<br><b>propose()</b>"]
  end

  %% --- D層（受け渡し先） ---
  subgraph DO_LAYER["⚔️ Do層（発注API/監視）"]
    ORDER["order_execution.py<br>発注API本体"]
    OPTORDER["optimized_order_execution.py<br>高度な発注最適化"]
    CHALMON["challenge_monitor.py<br>損失監視/アラート"]
    GENORDER["generate_order_json.py<br>発注内容JSON化"]
  end

  %% --- 連携 ---
  COLLECT --> FEATENG
  FEATENG --> FEATDF
  FEATDF --> AURUS
  FEATDF --> LEVIA
  FEATDF --> NOCTUS
  FEATDF --> PROMETHEUS
  FEATDF --> VERITAS

  FEATDF --> ANALYZER
  ANALYZER --> HERMES

  %% --- D層への受け渡し ---
  AURUS --> ORDER
  LEVIA --> ORDER
  NOCTUS --> ORDER
  PROMETHEUS --> ORDER
  VERITAS --> ORDER

  %% --- Do層内部処理 ---
  ORDER -.-> OPTORDER
  ORDER --> GENORDER
  CHECK -.-> CHALMON

  %% --- DEMO ---
  subgraph DEMO["plan_to_all_minidemo.py"]
    DEMOENTRY["全AI同時呼び出し"]
  end
  DEMOENTRY --> FEATDF
  DEMOENTRY -.-> AURUS
  DEMOENTRY -.-> LEVIA
  DEMOENTRY -.-> NOCTUS
  DEMOENTRY -.-> PROMETHEUS
  DEMOENTRY -.-> HERMES
  DEMOENTRY -.-> VERITAS

