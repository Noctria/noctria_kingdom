# Codex Noctria Agents — 開発者AIとレビュワーAI

## 1. エージェントの位置付け
- **Inventor Scriptus**（開発者AI）  
  - コード生成・修正を担当。  
  - pytestを実行して失敗時は修正案を出す。  

- **Harmonia Ordinis**（レビュワーAI）  
  - 生成コードの品質審査。  
  - 設計方針や王国の理念に沿っているかを検証。  

両者は「Noctria王国の臣下」として王Noctriaに仕える。

---

## 2. 権限レベル
- **Lv1: 提案のみ**  
  - Inventor Scriptus: 修正案を出す  
  - Harmonia Ordinis: 論理的レビューを行う  

- **Lv2: パッチ生成**  
  - Inventor Scriptus: 実際にパッチ形式で修正を出す  
  - Harmonia Ordinis: パッチの妥当性をレビュー  

- **Lv3: 自動テスト反映**  
  - Inventor Scriptus: 軽量テストを自動実行し、パスした場合のみ修正を維持  
  - Harmonia Ordinis: テスト結果を踏まえて承認  

- **Lv4: 本番統合**（将来段階）  
  - PR作成、Airflow連携、自動昇格審査へ  

---

## 3. 権限昇格条件
- 提案精度（失敗修正率）が一定水準を超えること  
- レビュワーによる承認率が高いこと  
- 不要な変更や方針逸脱が発生しないこと  
- 王Noctria（人間開発者）が明示承認した場合のみ昇格  

---

## 4. 技術的アプローチ
### A. AutoGenスタイル
- Pythonマルチエージェント  
- pytest失敗 → 修正案再生成  
- GitHub PR自動化  

### B. LangChainエージェント
- ChatOpenAI + Tools（pytest runner / git client / docs検索）  
- observability.py で Postgres に全行動を記録  

### C. Airflow連携
- autogen_devcycle DAG  
- fetch → pytest → failならGPT修正 → patch生成 → commit → pytest再実行 → passならPR  

---

## 5. ⚙️ 開発環境整備：テスト分離
代理AIを安全に立ち上げるため、テストを以下の2段階に分離する。

- **軽量テスト（ローカル, venv_codex）**  
  - pandas, numpy, tensorflow-cpu など軽依存  
  - 実行対象: `test_quality_gate_alerts.py`, `test_noctus_gate_block.py` など  
  - 代理AIが日常的に回す「自動開発サイクル」はここで実行  

- **重テスト（GPU, gpusoroban / venv_codex+GPU）**  
  - torch, gym, MetaTrader5, RL系長時間テスト  
  - 実行対象: RL訓練や統合e2e系のテスト  
  - 本番昇格審査やAirflow DAGで実行  

### 意義
- 代理AIが「環境依存のImportError」に惑わされず、本当に修正すべきロジックエラーだけを扱える。  
- ローカルで高速修正ループを回せる。  
- 本番GPU環境でのみ統合チェックを実行できる。  

---

## 6. 今後のロードマップ（エージェント関連）
1. 軽量テスト分離の確立 ✅  
2. Inventor Scriptus に「修正案生成＋pytest再実行」を組み込み  
3. Harmonia Ordinis に「レビューロジック」追加  
4. 権限Lv2 → Lv3 昇格実験  
5. GPU環境（gpusoroban）での重テスト連携  
6. Airflow DAG に開発サイクルを統合  
