# docs/codex/Codex_Noctria.md

# 🏰 Codex Noctria - 全体ロードマップとタスク表

## 1. 目的
Noctria王国における自律型AI開発体制の確立を目指す。  
中心となる王Noctriaが裁可を下し、臣下AIたち（Hermes, Veritas, Inventor Scriptus, Harmonia Ordinis）が開発を進める。

---

## 2. ロードマップ

### 🔹 短期 (段階1)
- **Inventor Scriptus (開発者AI)**: pytest失敗時に修正案をテキストで提示  
- **Harmonia Ordinis (レビュワーAI)**: pytestログを精査し、指摘を返す  
- **統合タスク**:
  - GUIからテスト実行ボタン
  - AutoGen/pytest runner の初期統合
  - Observability(DB) にログ記録

### 🔹 中期 (段階2)
- **Inventor Scriptus**: 自動パッチ生成（diffやファイル全体コード）
- **Harmonia Ordinis**: パッチレビューを自動化し、PRをapprove/reject
- **統合タスク**:
  - GitHub Actions連携でPR自動生成
  - PRレビュー履歴をPostgresに保存
  - FastAPI HUDに「PRレビュー」ページ

### 🔹 長期 (段階3)
- **Inventor Scriptus**: Airflow DAGによりnightly自動修正ループを実行
- **Harmonia Ordinis**: すべてのレビュー/決定をObservabilityへ記録
- **統合タスク**:
  - Airflow DAG `autogen_devcycle` の設計
  - observability.py を拡張してAI開発行動を記録
  - GUIに「自律開発進捗ダッシュボード」

### 🔹 最終 (段階4)
- **Inventor Scriptus**: 全工程を自律的に遂行
- **Harmonia Ordinis**: 自動マージとリリース承認を提案
- **王Noctria**: 「承認ボタン」だけで全開発が流れる
- **統合タスク**:
  - FastAPI HUDに「王の裁可UI」
  - PDCAループとAI開発サイクルを完全統合
  - GPUクラウドML + ChatGPT APIを両輪で活用

---

## 3. タスク表

| フェーズ | タスク | 担当AI |
|----------|--------|--------|
| 段階1 | pytest結果解析 → 修正案提示 | Inventor Scriptus |
| 段階1 | 修正案レビュー（自然言語） | Harmonia Ordinis |
| 段階2 | 自動パッチ生成 | Inventor Scriptus |
| 段階2 | 自動PRレビュー/approve | Harmonia Ordinis |
| 段階3 | nightly自律開発DAG実行 | Inventor Scriptus |
| 段階3 | 行動ログの可観測化 | Harmonia Ordinis |
| 段階4 | 全自律開発（承認UI） | Inventor Scriptus / Harmonia Ordinis / 王Noctria |

---
