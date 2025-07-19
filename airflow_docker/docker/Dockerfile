# airflow_docker/docker/Dockerfile
# Noctria Kingdom Airflow Image (v2.6)
FROM apache/airflow:2.9.2-python3.11

USER root

# ←★ここでgitをインストール！
RUN apt-get update && apt-get install -y git

USER airflow

# 依存パッケージをコピーしてインストール
COPY airflow_docker/requirements_extra.txt /requirements_extra.txt

RUN pip install --no-cache-dir -r /requirements_extra.txt
