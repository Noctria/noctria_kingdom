<!-- AUTODOC:BEGIN mode=file_content path_globs=/mnt/d/noctria_kingdom/docs/_partials_full/docs/Noctria_Kingdom_System_Design_v2025-08.md -->
# Noctria Kingdom System Design（v2025-08 統合版 + db_logging統合）

## 1. 目的と範囲
- プロジェクト全体の構造・責務・連携・運用ルールを**単一の真実**として管理
- PDCA（Plan–Do–Check–Act）循環を**DAG/コード/DB**で実装・観測・調整するための仕様
- **db_logging.py** による汎用DBイベントロギングを追加し、あらゆる層から統一記録可能にする

---

## 2. 全体アーキテクチャ（P/D/C/A）
- **Plan (P)**: 特徴量定義・戦略設計・ハイパラ探索  
  - `src/plan_data/*`, `src/scripts/optimize_params_with_optuna.py`
- **Do (D)**: 生成・学習・評価・昇格・発注  
  - 生成/学習: `src/veritas/*`, `src/training/*`  
  - 昇格: `src/scripts/apply_best_params_to_kingdom.py`  
  - 発注: `src/execution/*`
- **Check (C)**: 取引妥当性検証・運用監査・メトリクス収集  
  - DBテーブル: `validation_events`, `execution_events`, `perf_timeseries`, **`pdca_events`**  
  - ユーティリティ: `src/core/db_logging.py`, `src/core/utils.py`
- **Act (A)**: 政策更新・閾値調整・リリース手順  
  - `policies` / `policy_versions`（DB）、`src/core/risk_control.py`

---

## 3. PLAN層・Check層・AI臣下・Do層 全体構造

```mermaid
flowchart TD

  %% --- Plan層 ---
  subgraph PLAN["🗺️ PLAN層（特徴量生成・分析・戦略提案）"]
    COLLECT["plan_data/collector.py<br>市場データ収集"]
    FEATENG["plan_data/features.py<br>特徴量生成"]
    FEATDF["特徴量DataFrame/Dict出力"]
    ANALYZER["plan_data/analyzer.py<br>要因抽出/ラベル化"]
    STRAT["strategies/aurus_singularis.py<br>levia_tempest.py<br>prometheus_oracle.py"]
  end

  %% --- Check層 ---
  subgraph CHECK["🔍 Check層（リスク制御・監視）"]
    RISK["core/risk_control.py<br>Lot制限・リスク閾値チェック"]
    CHALMON_CHECK["execution/challenge_monitor.py<br>損失/異常アラート検知"]
  end

  %% --- AI臣下 ---
  subgraph AI_UNDERLINGS["🤖 臣下AI群（src/strategies/）"]
    AURUS["🎯 Aurus"]
    LEVIA["⚡ Levia"]
    NOCTUS["🛡️ Noctus"]
    PROMETHEUS["🔮 Prometheus"]
    HERMES["🦉 Hermes"]
    VERITAS["🧠 Veritas"]
  end

  %% --- Do層 ---
  subgraph DO_LAYER["⚔️ Do層（実オーダー執行/記録/最適化）"]
    ORDER["execution/order_execution.py"]
    OPTORDER["execution/optimized_order_execution.py"]
    CHALMON_DO["execution/challenge_monitor.py"]
    GENORDER["execution/generate_order_json.py"]
  end

  %% --- 接続 ---
  COLLECT --> FEATENG
  FEATENG --> FEATDF
  FEATDF --> AURUS
  FEATDF --> LEVIA
  FEATDF --> NOCTUS
  FEATDF --> PROMETHEUS
  FEATDF --> VERITAS
  FEATDF --> ANALYZER
  ANALYZER --> HERMES

  STRAT --> ORDER
  RISK --> ORDER
  RISK --> CHALMON_DO
  CHALMON_CHECK --> CHALMON_DO

  AURUS --> ORDER
  LEVIA --> ORDER
  NOCTUS --> ORDER
  PROMETHEUS --> ORDER
  VERITAS --> ORDER

  ORDER --> GENORDER
  ORDER -.-> OPTORDER
<!-- AUTODOC:END -->
```
