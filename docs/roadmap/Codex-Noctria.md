# 🏰 Codex Noctria — 自律型開発サイクル計画

> **王国の新たな構成要素**  
> Codex Noctria とは、Noctria 王国において **開発の自律化** を目指す新たな臣下群（Inventor Scriptus & Harmonia Ordinis）を中心とした構想である。  
> 彼らは Hermes Cognitor（LLM生成）と Veritas Machina（ML評価）、Prometheus Oracle（ML予測）と連携し、完全自律型の開発ループを稼働させる。

---

## 🎯 目的
- 人手による介入を最小限とし、Noctria 王国のシステムを自動で進化させ続ける
- LLM（言語生成）と ML（学習・評価）を分担し、創造と秩序を両立
- PDCA ループを超えた **「自律型 AI 開発サイクル」** を確立する

---

## 🤖 新たな臣下たち

### ✍️ Inventor Scriptus（開発者AI）
- コード生成を担う「開発者AI」
- pytest を駆動し、失敗時には修正案を生成
- GitHub に自動コミット／PR 作成
- Observability に開発ログを記録

### 🏛️ Harmonia Ordinis（レビュワーAI）
- レビューと秩序を担う「レビュワーAI」
- Scriptus のコードに改善点をフィードバック
- GitHub PR にレビューコメントを自動生成
- Observability にレビュー記録を保存

---

## 🧩 既存臣下との棲み分け

### Hermes Cognitor（LLM生成）
- 高次的な自然言語生成、仕様提案、文書作成を担当
- Scriptus の開発タスクを補助し、設計レベルの創造を行う

### Veritas Machina（ML評価）
- 戦略評価を担い、GPUクラウドでスコア計算を実施
- PDCA summary と突合し、採用／却下を判定

### Prometheus Oracle（ML予測）
- 市場予測・信頼区間計算を行い、評価に予測的視点を加える
- GUI に未来予測を表示し、王国の意思決定を支援

---

## ⚙️ 技術的アプローチ

### A. AutoGenスタイル（Pythonマルチエージェント）
- Scriptus（開発者AI）と Harmonia（レビュワーAI）の対話ループ
- tests/ を実行し、失敗時に修正案を生成 → 自動PR
- Microsoft Autogen のような仕組みを参考に構築

### B. LangChainエージェント
- ChatOpenAI + Tools（pytest runner / git client / docs検索）
- Plan層の observability.py を利用し、全行動を Postgres に記録
- 「NoctriaAgent」として動作

### C. Airflow連携
- AI開発サイクル自体を Airflow DAG 化
- DAG例: autogen_devcycle  
  - fetch 最新コード  
  - run pytest  
  - fail なら GPT に修正依頼  
  - patch 生成 → commit  
  - 再度 pytest  
  - pass したら PR

---

## 📅 ロードマップ

### フェーズ1 — 部分結合
- Hermes ↔ Scriptus の協働生成（仕様 + コード）
- Veritas ↔ Prometheus の GPU連携（予測 + 評価）
- Scriptus ↔ Harmonia の AutoGen風ループ

### フェーズ2 — 統合結合
- Codex Noctria DAG を Airflow に統合
- GUI ダッシュボードに Codex Noctria メトリクスを可視化
- 「日次自律開発ループ」を稼働

---

## ✅ タスクリスト

### Hermes Cognitor
- [ ] Codex Noctria の仕様書生成
- [ ] Scriptus の補助提案
- [ ] Observability に生成ログ保存

### Veritas Machina
- [ ] GPUクラウドでの戦略スコア算出
- [ ] 評価ログを Postgres 保存
- [ ] Airflow DAG に評価ステップ統合

### Prometheus Oracle
- [ ] GPUクラウドで市場予測ジョブ実行
- [ ] 予測結果を Postgres 保存
- [ ] GUI ダッシュボードに統合表示

### Inventor Scriptus
- [ ] pytest 自動実行と修正案生成
- [ ] GitHub PR 作成
- [ ] 開発ログを Observability に保存

### Harmonia Ordinis
- [ ] Scriptus のコードをレビュー
- [ ] GitHub PR に自動レビュー
- [ ] レビュー記録を Observability に保存

---

## 🗂️ 配置提案
- `docs/roadmap/Codex-Noctria.md`  
  → Codex Noctria 全体ロードマップ・タスク表（本書）

- `docs/architecture/Codex-Noctria-Agents.md`  
  → 技術的アプローチ・実装方式（AutoGen / LangChain / Airflow）を詳細化
