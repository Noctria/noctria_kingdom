# airflow_docker/docker/Dockerfile
# Noctria Kingdom Airflow Image (v2.6)
# ✅ ベースイメージをPython 3.11対応のバージョンに変更
FROM apache/airflow:2.9.2-python3.11

# airflowユーザーで以降の処理を実行
USER airflow

# 依存パッケージをコピーしてインストール
# ※ build.context が airflow_docker/ なので、1階層上が ./
COPY ../requirements_extra.txt /requirements_extra.txt

RUN pip install --no-cache-dir -r /requirements_extra.txt
