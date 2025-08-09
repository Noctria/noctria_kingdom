# Noctria Kingdom System Design（v2025-08 統合版）

## 1. 目的と範囲
- プロジェクト全体の構造・責務・連携・運用ルールを**単一の真実**として管理  
- PDCA（Plan–Do–Check–Act）循環を**DAG/コード/DB**で実装・観測・調整するための仕様

## 2. 全体アーキテクチャ（P/D/C/A）
- **Plan (P)**: 特徴量定義・戦略設計・ハイパラ探索  
  - `src/plan_data/*`, `src/scripts/optimize_params_with_optuna.py`
- **Do (D)**: 生成・学習・評価・昇格・発注  
  - 生成/学習: `src/veritas/*`, `src/training/*`  
  - 昇格: `src/scripts/apply_best_params_to_kingdom.py`  
  - 発注: `src/execution/*`（`src/noctria_ai/noctria.py` は現状ほぼ未使用）
- **Check (C)**: 取引妥当性検証・運用監査・メトリクス収集  
  - DBテーブル: `validation_events`, `execution_events`, `perf_timeseries`  
  - ユーティリティ: `src/core/utils.py` の `log_*` 群
- **Act (A)**: 政策更新・閾値調整・リリース手順  
  - `policies` / `policy_versions`（DB）、`src/core/risk_control.py`（反映先）

## 3. 主要コンポーネントと責務
- **データ取得（正規API）**: `src/core/data/market_data_fetcher.py: MarketDataFetcher`  
  - `fetch(source="yfinance"|"alphavantage")` で統一  
  - Alpha Vantage は `src/core/data_loader.py` をブリッジ（※Deprecation 警告あり）
- **経路依存の吸収**: `src/core/path_config.py`（ルート/データ/GUI/DAG など全パス）  
- **DAG群**: `airflow_docker/dags/*`
  - `noctria_kingdom_dag.py`: 定時の観測→（前検証）→会議→記録
  - `noctria_kingdom_pdca_dag.py`: Optuna → MetaAI適用 → Kingdom昇格 → 王決断
- **モデル昇格**: `src/scripts/apply_best_params_to_kingdom.py`  
  - `models/official/model_registry.json` を更新・履歴管理
- **GUI**: `noctria_gui/*`（ダッシュボード/戦略一覧/履歴表示）

## 4. PLAN層・AI臣下・Do層 全体構造（組み込み）
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

  %% --- D層（受け渡し先のみ） ---
  subgraph DO_LAYER["⚔️ Do層（受け渡し先）"]
    ORDER["order_execution.py<br>発注API本体"]
  end

  %% --- 連携 ---
  COLLECT --> FEATENG
  FEATENG --> FEATDF
  FEATDF -->|最新dict/DF/feature_order| AURUS
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

  %% --- サンプルデモ ---
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

  %% --- 装飾 ---
  classDef plan fill:#262e44,stroke:#47617a,color:#d8e0f7
  classDef ai fill:#333,color:#ffe476,stroke:#a97e2c
  classDef demo fill:#25252a,stroke:#f6e58d,color:#fffaad
  classDef do fill:#3d2d2d,stroke:#cc9999,color:#ffcccc

  class PLAN plan
  class AI_UNDERLINGS ai
  class DEMO demo
  class DO_LAYER do

  %% --- 補足 ---
  %% click DEMOENTRY "https://github.com/your_repo/src/plan_data/plan_to_all_minidemo.py" "サンプル実装ファイル"
