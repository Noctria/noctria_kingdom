#!/bin/bash
# ==============================================
# 🔧 Airflow 初期化 & 管理者ユーザー作成スクリプト
# - airflow db upgrade を実行して初期化
# - admin/admin のユーザーが存在しない場合、自動作成
# - その後、本来の Airflow コマンドを実行（webserver 等）
# ==============================================

set -e  # エラー時即終了

echo "🔧 Step 1: Airflow データベース初期化"
airflow db upgrade

echo "👤 Step 2: 管理者ユーザーの作成を確認中..."
python /opt/airflow/tools/create_admin_user.py

echo "🚀 Step 3: Airflow サービス起動 → airflow $@"
exec airflow "$@"
