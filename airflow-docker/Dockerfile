# ベースイメージは Airflow 3.0.2 の Python 3.9 スリム版を指定
FROM apache/airflow:slim-3.0.2-python3.9

USER root

# OSレベルで必要な開発ツール類をインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git build-essential cmake \
        python3-dev zlib1g-dev libbz2-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# requirements.txt を先にコピーしてキャッシュレイヤーを確保
COPY requirements.txt /requirements.txt

# 制約ファイル付きインストールで環境再現性を保持
RUN pip install \
    "apache-airflow==3.0.2" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.0.2/constraints-3.9.txt" && \
    pip install --no-cache-dir -r /requirements.txt && \
    pip install --no-cache-dir tensorflow==2.19.0 yfinance==0.2.62

USER airflow
