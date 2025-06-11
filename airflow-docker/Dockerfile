FROM apache/airflow:2.8.0

# rootユーザーで追加パッケージをインストール
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# airflowユーザーに切り替え
USER airflow

# 追加のpipライブラリをrequirements.txtからインストール
COPY requirements.txt /requirements.txt

# 🟢 追加のpip install (statsmodels, blosc2)
RUN pip install --no-cache-dir -r /requirements.txt \
    && pip install --no-cache-dir statsmodels blosc2

# airflowユーザーでコンテナ起動（デフォルト）
