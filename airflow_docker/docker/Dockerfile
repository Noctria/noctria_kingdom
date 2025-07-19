# ===========================================
# Noctria Kingdom - Airflowカスタムイメージ
# ベース: Apache Airflow 2.9.2 + Python 3.11
# ===========================================

FROM apache/airflow:2.9.2-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Python依存ファイルをイメージにコピー
COPY airflow_docker/requirements.txt /requirements.txt
COPY airflow_docker/requirements_extra.txt /requirements_extra.txt

# 依存パッケージをインストール
RUN pip install --no-cache-dir -r /requirements.txt \
    && pip install --no-cache-dir -r /requirements_extra.txt
