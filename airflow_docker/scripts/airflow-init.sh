#!/bin/bash

set -e

echo "⚙️ 初期化開始：Airflow Database & ユーザー設定"

# Airflow DB 初期化 & マイグレーション
airflow db check || true
airflow db init

# Admin ユーザー作成（存在しない場合のみ）
echo "👤 Admin ユーザーを作成..."
airflow users create \
    --username admin \
    --firstname Noctria \
    --lastname Admin \
    --role Admin \
    --email admin@noctria.ai \
    --password admin || true

# Optuna DB接続情報を Airflow Connections に登録
echo "🔗 Optuna DB 接続情報を airflow connections に登録..."
airflow connections delete optuna_db || true
airflow connections add optuna_db \
    --conn-uri "${OPTUNA_DB_URL}"

# HuggingFace Token の XCom 共有・キャッシュ指定用
echo "🔐 HuggingFace Token 接続情報を airflow connections に登録..."
airflow connections delete huggingface_token || true
airflow connections add huggingface_token \
    --conn-type generic \
    --extra "{\"token\": \"${HF_TOKEN}\", \"hf_home\": \"${HF_HOME}\"}"

echo "✅ Airflow 初期化完了"
