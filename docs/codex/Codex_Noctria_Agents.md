# ⚙️ Codex Noctria Agents — 技術的アプローチ・実装方式

本書は **Codex-Noctria.md（全体ロードマップ）** を補完し、Noctria 王国における代理AI（Inventor Scriptus / Harmonia Ordinis）および Hermes・Veritas の自律開発サイクルを支える技術的方式を記述する。

---

## 1. 技術的アプローチ

### A. AutoGen スタイル（Pythonマルチエージェント）
- **Inventor Scriptus**（開発者AI）と **Harmonia Ordinis**（レビュワーAI）を並走
- pytest を実行 → 失敗したら修正案生成 → 再試行
- 成功時に GitHub PR を自動化
- 利点: 自律的開発ループをシンプルに構築可能

### B. LangChain エージェント
- LangChain + ChatOpenAI を利用し、NoctriaAgent を実装
- Tools:
  - pytest runner
  - git client
  - docs 検索
- observability.py 経由で Postgres に全行動を記録可能
- 利点: 強い拡張性、toolchain の容易な追加

### C. Airflow 連携
- **AI開発サイクルそのものを DAG 化**
- 例: `autogen_devcycle` DAG
  1. 最新コード fetch
  2. pytest 実行
  3. 失敗なら GPT に修正依頼
  4. パッチ生成 → commit
  5. pytest 再実行
  6. 成功時に GitHub PR
- 利点: スケジューラ・監視・再実行が標準化される

---

## 2. 実装方式（臣下ごと）

### Inventor Scriptus（開発者AI）
- ChatGPT API を利用
- pytest ログを解析し、修正案コードを生成
- `generated_code/` にパッチ保存
- GitHub CLI または pygit2 で PR 作成

### Harmonia Ordinis（レビュワーAI）
- Scriptus 提案を精査
- コード規約・依存性・統治ルールとの整合性を検証
- 自動レビューコメントを生成し、PR に付与
- 重大リスクがあれば **REJECT**

### Hermes Cognitor（LLM戦略生成AI）
- LLM API（ChatGPT）で戦略アイデアを自然言語から生成
- 提案戦略をコード化（EA / Python戦略）
- Veritas への入力フォーマットに変換

### Veritas Machina（ML評価AI）
- GPUクラウドで戦略を訓練
- 評価: 勝率 / 最大DD / Sharpe / RMSE / MAPE
- 評価結果を Hermes にフィードバックし、改善ループを形成

---

## 3. 部分結合・統合結合の工程

- **部分結合**
  - Hermes + Veritas … 戦略生成と評価の自動ループ
  - Scriptus + Harmonia … コード修正とレビューの開発ループ
- **統合結合**
  - 全エージェントを Airflow DAG に統合
  - Observability (Postgres) で統一的に行動ログを保存
  - King Noctria が最終裁定を自動下す

---

## 4. 使用インフラ

- **LLM**: OpenAI ChatGPT API（Hermes / Scriptus / Harmonia）
- **ML**: GPUクラウドサービス（AWS / GCP / Azure）
- **Orchestration**: Apache Airflow
- **Logging**: PostgreSQL（observability.py）
- **CI/CD**: GitHub Actions + PR 自動生成

---

## 5. 今後の拡張
- 🛠️ CI/CD → GitHub Actions から Airflow DAG へ移行
- 🧠 複数 LLM モデルを併用（Hermes=GPT-4.1, Scriptus=GPT-5-mini）
- 🔄 PDCAループ全体の完全自動化
- 🏰 王の意思決定を「Chain-of-Council」としてモデル化

---
