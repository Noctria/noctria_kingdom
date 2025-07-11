#!/bin/bash
echo "🚨 クリーンアップ開始（第3版: 重複構造・キャッシュ含む）"

# ─── 🧹 Python キャッシュ ───
find . -type d -name '__pycache__' -exec rm -rf {} +
find . -type f -name '*.pyc' -delete

# ─── 🗑 重複ディレクトリ（airflow_docker 側） ───
rm -rf airflow_docker/core
rm -rf airflow_docker/config
rm -rf airflow_docker/data
rm -rf airflow_docker/scripts
rm -rf airflow_docker/strategies

# ─── 🗑 重複ディレクトリ（ルート側 dags の方が古い場合） ───
rm -rf dags

echo "✅ クリーンアップ完了（第3版）"
