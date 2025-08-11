# 📜 Noctria Kingdom プロジェクト INDEX（標準引き継ぎ用）

## 1. 目的
Noctria Kingdom プロジェクトの全体像・統治構造・役割分担・開発方針を明確化し、  
スレッドや担当が変わっても方針がぶれず、開発資産が適切に管理される状態を維持する。

---

## 2. プロジェクト全体像
Noctria Kingdom は、中央統治AI「King Noctria」を頂点とした複数の専門AI臣下により、  
市場戦略の生成・評価・実行・改善を自動化する統治型金融AIシステム。

- **中央統治AI**  
  - `src/core/king_noctria.py`  
  - 最終意思決定者。臣下AIの提案を統合し、王国の富と安定を最大化。

- **臣下AI**
  | AI名 | ファイル | 役割 |
  |------|----------|------|
  | Aurus Singularis | `src/strategies/Aurus_Singularis.py` | 市場解析・総合戦略立案 |
  | Levia Tempest | `src/strategies/Levia_Tempest.py` | 高速スキャルピング戦略 |
  | Noctus Sentinella | `src/strategies/Noctus_Sentinella.py` | リスク評価・資本保護 |
  | Prometheus Oracle | `src/strategies/Prometheus_Oracle.py` | 中長期予測・未来指針 |
  | Veritas | `src/veritas/` | 戦略生成・MLによる最適化 |
  | Hermes Cognitor | `src/hermes/` | 戦略説明・自然言語化 |

---

## 3. 統治レイヤー構造

1. **中央統治レイヤ（最終決定）**  
   - `king_noctria.py`  
   - `airflow_docker/dags/noctria_kingdom_pdca_dag.py`  
   - `airflow_docker/dags/noctria_kingdom_dag.py`

2. **PDCAサイクル**
   - **Plan**: データ収集〜特徴量生成（`src/plan_data/`）  
   - **Do**: 各AI戦略実行（`src/strategies/`）  
   - **Check**: 評価・統計分析（`src/evaluation/`）  
   - **Act**: 改善・再学習（`src/veritas/`, Airflow DAG）

3. **Airflowによる自動化**
   - 学習DAG例: `train_prometheus_obs8`  
   - 推論DAG例: `oracle_prometheus_infer_dag.py`（※新設時は要理由）

---

## 4. GUI構造
- **基盤**: FastAPI + Jinja2 + Tailwind/HUDスタイル
- **主要ルート**
  | 機能 | ルート | テンプレート |
  |------|-------|--------------|
  | ダッシュボード | `/dashboard` | `dashboard.html` |
  | PDCA履歴 | `/pdca/history` | `pdca_history.html` |
  | 戦略比較 | `/strategies/compare` | `compare_result.html` |
  | 王の決定 | `/king` | `king_history.html` |

---

## 5. 開発・運用ルール
1. 新規ファイルは必ずディレクトリ構造と役割を確認  
2. 類似機能は統合し、ファイル乱立を避ける  
3. DAG・戦略ファイルは必ずAirflow上で動作確認  
4. GUIテンプレートはHUDスタイルに統一（`base_hud.html`継承）  
5. Pull Request前に`docs/CHANGELOG.md`更新

---

## 6. 優先ドキュメント一覧
以下の詳細ドキュメントは `docs/` 各サブディレクトリに配置し、  
ここからリンクする。

1. [アーキテクチャ図](../architecture/architecture_overview.md)
2. [PDCA構造詳細](../workflows/pdca_cycle.md)
3. [臣下AI仕様書](../governance/ai_underlings.md)
4. [Airflow DAG仕様書](../workflows/airflow_dags.md)
5. [GUIルート仕様書](../gui/gui_routes.md)
6. [モデル管理ポリシー](../models/model_management.md)
7. [開発フローとルール](../governance/dev_rules.md)
8. [運用ガイド](../governance/operations.md)
9. [トラブルシューティング](../governance/troubleshooting.md)
10. [ADR: 重要な技術選択記録](../adrs/)

---

## 7. 更新履歴
- **2025-08-12**: 初版作成

