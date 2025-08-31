# docs/codex/Codex_Noctria_Agents.md

# 🤖 Codex Noctria Agents - 技術的アプローチと権限レベル

## 1. 技術的アプローチ

### A. AutoGenスタイル（Pythonマルチエージェント）
- Inventor Scriptus と Harmonia Ordinis がエージェントとして会話
- pytest失敗時 → 修正案生成 / レビュー
- GitHub PRを自動化可能

### B. LangChainエージェント
- ChatOpenAI + Tools(pytest runner, git client, docs検索)
- Plan層の observability.py を利用し、行動をPostgresに記録
- 「NoctriaAgent」としてHUDから実行可能

### C. Airflow連携
- AI開発サイクルそのものを Airflow DAG 化
- DAG例: `autogen_devcycle`
  1. fetch 最新コード
  2. run pytest
  3. fail → GPT修正案生成
  4. patch → commit
  5. 再度 pytest
  6. pass → PR作成

---

## 2. 権限レベル設計

### 権限レベル 1: 助言フェーズ
- **Inventor Scriptus**: 修正提案をテキスト提示
- **Harmonia Ordinis**: pytestログを解析し自然言語でレビュー
- 実装: AutoGen + pytest log parser

### 権限レベル 2: 自動パッチフェーズ
- **Inventor Scriptus**: 修正コードを生成しPRを作成
- **Harmonia Ordinis**: PRをレビューしapprove/reject
- 実装: GitHub Actions + LangChain agent

### 権限レベル 3: 自律結合フェーズ
- **Inventor Scriptus**: nightly Airflow DAGで修正を自動実行
- **Harmonia Ordinis**: Observabilityに行動を記録
- 実装: Airflow DAG + observability.py

### 権限レベル 4: 王裁可フェーズ
- **Inventor Scriptus**: 全工程を自律的に完遂
- **Harmonia Ordinis**: 自動リリース承認提案
- **王Noctria**: GUIから承認を与えるだけで全体が進行
- 実装: FastAPI HUD + 「王の裁可」UI

---
