# Noctria Kingdom 開発ナレッジベース

## パス管理
- パス定義は全てsrc/core/path_config.pyで集中管理。直書き厳禁。

## テスト
- テストファイルには必ずpytest/unittest形式を採用。日本語文字列には注意（SyntaxError回避）。

## 仮想環境・コンテナ
- Airflowはairflow_docker/配下docker、noctria_guiはvenv_gui、noctria本体はvenv_noctria、AIスクリプトはautogen_venv。

## コーディング
- PEP8＋型アノテ＋Black/isort必須。
- 依存パッケージは各requirements.txtで明示管理。
