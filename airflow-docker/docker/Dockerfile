# 初回ビルド（torch含む）
cd airflow-docker
docker compose build

# DB初期化
docker compose up airflow-webserver airflow-scheduler postgres -d
docker compose exec airflow-webserver airflow db init

# ユーザー作成（初回のみ）
docker compose exec airflow-webserver airflow users create \
  --username admin --firstname Noctria --lastname King \
  --role Admin --email admin@example.com --password yourpassword
