#!/bin/bash

# ===========================
# 🌀 Airflow 初期化処理
# ===========================

echo "🔧 Step 1: Initializing Airflow DB..."
airflow db init

echo "👤 Step 2: Creating admin user if not exists..."
python /opt/airflow/create_admin_user.py

# ===========================
# 🚀 Airflow 本体起動
# ===========================
echo "🚀 Step 3: Launching Airflow $@ ..."
exec airflow "$@"
