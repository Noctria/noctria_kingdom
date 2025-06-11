FROM apache/airflow:2.8.0

# rootユーザーで追加パッケージをインストール
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

# airflowユーザーに切り替え
USER airflow

# 追加のpipライブラリをrequirements.txtからインストール
COPY requirements.txt /requirements.txt

# ✅ blosc2は除外！ statsmodelsだけ手動インストール
RUN /usr/local/bin/pip install --no-cache-dir -r /requirements.txt && \
    /usr/local/bin/pip install --no-cache-dir statsmodels

# airflowユーザーでコンテナ起動（デフォルト）
