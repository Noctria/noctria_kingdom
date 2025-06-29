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
    git \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# ✅ CeleryExecutor に必要な追加パッケージ
RUN pip install --no-cache-dir \
    'apache-airflow[celery]==2.9.1' \
    'flower' \
    'redis'

USER airflow

# ✅ PYTHONPATH を Airflow 全体に適用
ENV PYTHONPATH=/noctria_kingdom/airflow_docker

# ✅ requirements.txt をコピー
COPY requirements.txt /requirements.txt

# ✅ Pythonライブラリのインストール（CPU限定のTorch含む）
RUN pip install --upgrade pip && \
    pip install --no-cache-dir torch==2.2.2+cpu --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
        pytest \
        transformers \
        accelerate \
        sentencepiece \
        huggingface-hub \
        einops \
        peft && \
    pip install --no-cache-dir -r /requirements.txt
