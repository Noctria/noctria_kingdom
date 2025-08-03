# ファイル名: path_config.py
# バージョン: v0.1.0
# 生成日時: 2025-08-04T01:42:08.801336
# 生成AI: openai_noctria_dev.py
# UUID: 16e6148c-d354-4cbc-9f1b-211126ba8539
# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。

# ディレクトリパスやファイルパスを集中管理するモジュール
# PEP8に準拠し、全てのパス定義に型注釈を追加します。

from typing import Final

# データソースURL
DATA_SOURCE_URL: Final[str] = "http://example.com/data_source"

# ローカルデータパス
LOCAL_DATA_PATH: Final[str] = "/path/to/local_data"

# 特徴量データパス
FEATURES_PATH: Final[str] = "/path/to/features"

# モデルファイルパス
MODEL_PATH: Final[str] = "/path/to/model"
