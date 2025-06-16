FROM apache/airflow:2.9.1-python3.10

USER root

# ✅ システム依存パッケージのインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# ✅ 依存ライブラリをコピー（Airflow起動時に必要なAIモジュール群）
COPY requirements.txt /requirements.txt

# ✅ torch（CPU版）およびその他パッケージをインストール
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
        torch==2.2.2+cpu \
        --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /requirements.txt
