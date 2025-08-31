# Codex Noctria Agents

## 🧑‍💻 Inventor Scriptus（開発者AI）
- **役割**: コード生成・修正案の提示  
- **初期権限**: 提案（Pull Request 下書きまで）  
- **特徴**:  
  - pytest を回し、失敗時に修正案を生成  
  - GitHub PR を自動作成可能  
  - Airflow DAG のコード化支援  

---

## 🧾 Harmonia Ordinis（レビュワーAI）
- **役割**: 提案コードの検証・レビューレポート作成  
- **初期権限**: 助言・レビューのみ  
- **特徴**:  
  - Inventor Scriptus の提案を静的解析 & pytest で確認  
  - レビューコメントを生成し、可視化ログに残す  
  - 危険な変更をブロック可能  

---

## ⚖️ 権限レベル（昇格ステップ）

| レベル | 権限範囲 | 判断基準 |
|--------|-----------|-----------|
| **Lv1: 助言** | テキスト提案のみ | - 修正案の 70%以上 が人間レビューで有効 |
| **Lv2: 自動パッチ** | pytest 修正案を自動生成・PR化 | - 自動生成パッチのテスト pass率が高い<br>- 人間レビューで reject率が低い |
| **Lv3: 自律結合** | 自動PR結合、Airflow連携の自律実行 | - 1か月の PR accept率 80%以上<br>- テスト pass率 90%以上 |
| **Lv4: 王裁可** | 自律統合＋Airflow DAG運用 | - 3か月事故ゼロ<br>- 全行動が観測ログに記録<br>- 王（Noctria）の承認済み |

---

## 🔍 技術的アプローチ
- **AutoGen スタイル**: 開発者AIとレビュワーAIを対話させ、失敗時に再生成  
- **LangChain Agent**: pytest runner / git client / docs検索を Tool として利用可能  
- **Airflow 連携**: AI開発サイクル自体を DAG 化（autogen_devcycle DAG）  

---

## 📊 メトリクス管理
- **収集**: テスト pass率、PR accept率、事故件数を Postgres に格納  
- **透明性**: Harmonia Ordinis によるレビューレポートを必須化  
- **GUI統治**: HUD 上に「権限昇格提案」パネルを設置し、王が承認するまで昇格しない  

---

## 🏰 統治フロー
1. Inventor Scriptus が提案を作成  
2. Harmonia Ordinis がレビュー & レポート提出  
3. Postgres に結果を記録（成功率・失敗率）  
4. 権限昇格条件を満たしたら Harmonia Ordinis が昇格提案  
5. 王 Noctria が最終承認  

---
