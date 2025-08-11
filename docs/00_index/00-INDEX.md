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

## 6. ドキュメント一覧（1〜21）
以下は `docs/` 配下の主要ドキュメントとリンク。

1. [00-INDEX.md](../00_index/00-INDEX.md) – 本ファイル。全体索引  
2. [Vision-Governance.md](../governance/Vision-Governance.md) – プロジェクト理念・統治モデル  
3. [Architecture-Overview.md](../architecture/Architecture-Overview.md) – アーキテクチャ概要図  
4. [Runbooks.md](../operations/Runbooks.md) – 運用手順書  
5. [Config-Registry.md](../operations/Config-Registry.md) – 設定管理ポリシー  
6. [Airflow-DAGs.md](../operations/Airflow-DAGs.md) – DAG構造・運用ガイド  
7. [ModelCard-Prometheus-PPO.md](../models/ModelCard-Prometheus-PPO.md) – モデル仕様書  
8. [Strategy-Lifecycle.md](../models/Strategy-Lifecycle.md) – 戦略ライフサイクル  
9. [Plan-Layer.md](../architecture/Plan-Layer.md) – Plan層詳細  
10. [API.md](../apis/API.md) – API仕様書  
11. [Observability.md](../observability/Observability.md) – モニタリングと可観測性  
12. [Security-And-Access.md](../security/Security-And-Access.md) – セキュリティとアクセス制御  
13. [Testing-And-QA.md](../qa/Testing-And-QA.md) – テスト戦略と品質保証  
14. [Release-Notes.md](../roadmap/Release-Notes.md) – リリースノート  
15. [Roadmap-OKRs.md](../roadmap/Roadmap-OKRs.md) – 中長期計画・OKR  
16. [Coding-Standards.md](../governance/Coding-Standards.md) – コーディング規約  
17. [ADRs](../adrs/) – 重要な技術選定の記録（Architecture Decision Records）  
18. [Incident-Postmortems.md](../incidents/Incident-Postmortems.md) – インシデント事後分析  
19. [Do-Layer-Contract.md](../apis/Do-Layer-Contract.md) – Do層API契約仕様  
20. [Risk-Register.md](../risks/Risk-Register.md) – リスク登録簿  
21. [howto-*.md](../howto/) – ハウツー集

---

## 7. 更新履歴
- **2025-08-12**: 初版作成
- **2025-08-12**: ドキュメント一覧を1〜21へ拡充
