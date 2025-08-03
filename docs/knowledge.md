# Noctria Kingdom 開発ナレッジベース

## 開発環境・実行基盤
- Windows PC上でWSL2（Ubuntu）を利用している。
- `noctria_kingdom/airflow_docker/` 内は **AirflowのDockerコンテナ**（Linux）で動作。
- `noctria_kingdom/noctria_gui/` 内は **WSL側 venv（venv_gui）** で動作。
- `noctria_kingdom/` 本体は **WSL側 venv（venv_noctria）** で動作。
- このAI自動化スクリプトは **WSL側 venv（autogen_venv）** で稼働。
- Docker（Airflow）とWSL側Pythonはファイル共有できる部分とできない部分がある。設計時は**パス・データ連携方法・依存管理**を明確にする。
- venvごとのpip依存（venv_noctria, venv_gui, autogen_venv等）が混じらないよう注意。

## パス管理
- すべてのパス定義（ディレクトリやファイルパス等）は **src/core/path_config.py** で集中管理する。
- 他のPythonファイルでは**パス文字列を直書き禁止**。必ず `path_config.py` からimportすること。
- 既存コードでのパス直書き・os.path.join等の分散パス指定も**path_config.pyへ統合**。

## コード実装ルール
- 複数ファイルに分割する場合は **先頭に必ず `# ファイル名: filename.py` を記載**。
- PEP8準拠・型アノテーション必須。
- 例外処理を適切に実装。
- コードはUTF-8で保存。
- Black/isortでコード整形を想定。

## テスト・レビュー
- テストはunittestまたはpytest形式で統一。
- テストファイルでもパスは必ず `path_config.py` からimport。
- 正常系/異常系/連携系のテストもカバー。
- 生成物（コード・テスト）が全て `path_config.py` のパス集中管理ルールを守っているかレビュー時に厳格にチェック。

## ドキュメント
- path_config.pyによるパス集中管理の意義・設計思想・利用例はREADMEやドキュメントで明記。

## その他・運用
- Git連携（add/commit/push）は自動スクリプト内で実施（失敗時は手動確認）。
- ユーザーコマンドでワークフロー一時停止・終了可能。

---

**このナレッジベースの内容は常に全AIが最優先で遵守すること。**
