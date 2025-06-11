# ベースイメージ（Airflow公式）
FROM apache/airflow:2.8.0

# rootユーザーで必要パッケージインストール
USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        cmake \
        python3-dev \
        zlib1g-dev \
        libbz2-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 先にrequirements.txtだけコピー（キャッシュ最適化）
COPY requirements.txt /requirements.txt

# requirements.txtに記載されたパッケージ群をまとめてインストール
RUN /usr/local/bin/pip install --no-cache-dir -r /requirements.txt

# tensorflow, yfinanceなどは個別に明示インストール
# 依存衝突を回避するためにrequirements.txtの後で実行
RUN /usr/local/bin/pip install --no-cache-dir tensorflow yfinance

# airflowユーザーに戻す
USER airflow

# Airflowコンテナは Airflow本体が Entrypointで立ち上がるので、
# これ以降に必要な設定（環境変数など）は docker-compose.yml で管理します
