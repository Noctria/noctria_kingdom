#!/bin/bash

# ===============================
# 🛠️ Noctria Kingdom Airflow 初期化スクリプト
# ===============================

set -e

echo "📦 Airflow DB 初期化開始..."
airflow db init

echo "👤 ユーザー作成: admin / admin"
airflow users create \
    --username admin \
    --firstname Noctria \
    --lastname Administrator \
    --role Admin \
    --email noctria@kingdom.ai \
    --password admin || echo "⚠️ 既にユーザーが存在します。スキップ"

echo "🔌 PostgreSQL Optuna 接続登録（optuna_db）..."
if [ -z "$OPTUNA_DB_URL" ]; then
  echo "❌ .env に OPTUNA_DB_URL が定義されていません。スキップします。"
else
  airflow connections add 'optuna_db' \
    --conn-uri "${OPTUNA_DB_URL}" \
    --conn-type 'postgres' \
    --conn-description "Optuna Study DB" || echo "⚠️ optuna_db 接続は既に存在。スキップ"
fi

echo "✅ 初期化完了。Airflow 起動準備OK。"
