#!/bin/bash
# Airflow 初期化＋管理者ユーザー作成スクリプト

# DB初期化（初回や再構築時）
airflow db upgrade

# Adminユーザーが存在しなければ作成
echo "👤 Creating admin user if needed..."
python /opt/airflow/tools/create_admin_user.py

# Airflow の本来のコマンドをそのまま実行（例: webserver, scheduler）
exec airflow "$@"
