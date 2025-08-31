# 📜 Codex Noctria — 王国全体ロードマップ・タスク表

## 1. 王国の目的
Noctria Kingdom の開発を完全自律型に進化させる。  
AI臣下（Hermes, Veritas, Prometheus, Inventor Scriptus, Harmonia Ordinis）と中央統治AI（King Noctria）が連携し、戦略生成から検証、意思決定、運用までを **自己循環するPDCAループ** として実現する。

---

## 2. 臣下の役割
- **Hermes Cognitor (LLM)**  
  ChatGPT API を利用して自然言語から戦略案・改善点を生成。
- **Veritas Machina (ML)**  
  GPUクラウド環境で戦略を訓練・評価する。精度・勝率・リスクを数値化。
- **Prometheus Oracle**  
  市場の未来予測（信頼区間付き）を提示し、戦略に前提を与える。
- **Inventor Scriptus (開発者AI)**  
  コード生成と修正案の自動適用。テスト失敗時に修正を試みる。
- **Harmonia Ordinis (レビュワーAI)**  
  提案コードや修正をレビューし、王国全体の調和を守る。

---

## 3. フェーズ別ロードマップ
### Phase 1: 基盤整備（現状）
- ✅ PDCAループの基本実装（Plan/Do/Check/Act）
- ✅ Observability層によるログ蓄積（Postgres）
- ✅ GUI（HUDスタイル）での可視化

### Phase 2: 代理AIの導入
- Scriptus ↔ Harmonia による **自動開発ループ**
- Pytest 実行 → 失敗時に修正案生成 → 再実行
- 成功した修正は GitHub PR に自動反映

### Phase 3: 結合フェーズ
- Hermes（LLM戦略）と Veritas（ML評価）を部分結合
- Prometheus の未来予測を Hermes 戦略生成に統合
- Noctus Gate / Quality Gate による自動フィルタリング強化

### Phase 4: 統合自律型 Noctria
- 全エージェントが Airflow DAG に統合
- 完全自律の開発サイクル（AutoGen + LangChain + Airflow）
- 王Noctriaによる「最終裁定」プロセスの自動化

---

## 4. タスクリスト（臣下ごと）

### Hermes Cognitor
- [ ] LLM API（ChatGPT）を利用した戦略提案生成
- [ ] 生成プロンプトの最適化（過去ログ・observability反映）
- [ ] Veritas の評価を参照して再提案ループ

### Veritas Machina
- [ ] GPUクラウドで戦略を訓練・評価
- [ ] KPI（勝率, DD, Sharpe, MAPE）の計算
- [ ] Hermes提案との統合比較

### Prometheus Oracle
- [ ] 未来予測と信頼区間のダッシュボード表示
- [ ] Hermes戦略生成への前提入力

### Inventor Scriptus
- [ ] pytest 実行と失敗ログ解析
- [ ] 修正案生成とパッチ適用
- [ ] GitHub PR 自動化フロー

### Harmonia Ordinis
- [ ] Scriptus 提案のレビュー（安全性・整合性）
- [ ] コーディング規約・アーキテクチャ整合性チェック
- [ ] 王への最終報告（合格/却下）

---

## 5. 統治ルール
- **部分結合 → 統合結合のロードマップ**
  - 部分結合: Hermes + Veritas, Scriptus + Harmonia の対
  - 統合結合: Airflow DAG 内で全臣下を連結
- **すべての行動を Observability に記録**
- **最終決定は常に King Noctria が行う**

---

## 6. 完全自律型に至るビジョン
最終的に Noctria Kingdom は以下を実現する：  
- 戦略の生成・評価・採用を **人間の介入なしに自律実行**  
- バージョン管理と GitHub PR を自動化  
- 市場変化に即応する Adaptive PDCA サイクル  

---
