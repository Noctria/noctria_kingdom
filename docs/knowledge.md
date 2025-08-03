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

## 中央統治・注文執行ルール
- Noctria Kingdomにおける**最終的な意思決定・注文の実行は必ず `src/core/king_noctria.py` を唯一のエントリーポイントとして実施すること**。
- 各AIエージェント・コンポーネントは king_noctria.py を経由せずに直接注文・アクションを発行してはならない。
- 新規機能や拡張時も必ず king_noctria.py への集約設計・統治フローを守ること。
- GUIやAPI、Airflowからの注文・アクション要求も、king_noctria.py を通じて判断・執行される構造に統一すること。

## GUIスタイル・HUD統一ルール
- Noctria KingdomのGUI管理ツール（`noctria_kingdom/noctria_gui/`配下）は**すべてのHTMLテンプレート・ページを `noctria_gui/static/hud_style.css` に準拠したHUDスタイルで開発・統一すること**。
- デザインやレイアウトを修正・追加する際は、**必ずhud_style.cssの定義・トークンを優先利用し、HUDデザインと一貫性を保つ**。
- 独自CSSやインラインスタイルの利用は原則避け、hud_style.cssのカスタムプロパティ・クラスを活用すること。
- HUDデザインに則ったパネル・グロー・ダークテーマ・モノスペースフォント・グリッド背景などを標準とする。

## Veritas MLクラウド運用ポリシー
- Veritas（ML/AI関連機能）は**将来的にAWS/GCP/AzureなどのGPUクラウドサービス上でトレーニング・推論を行うことを前提**に設計・実装すること。
- コードは「ローカル/WSL環境」だけでなく「GPUクラウド（JupyterHub, Sagemaker, Vertex AI等）」での利用や拡張を常に意識。
- ハードウェア・クラウド環境依存を避け、**パス・依存・データ転送等は分離設計**とする。
- 学習・推論ジョブは将来的にAirflow/Dockerから外部クラウドにトリガーできる構造も想定すること。
- モデル出力/成果物のパスもクラウド/オンプレ両対応設計。

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
