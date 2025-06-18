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

USER airflow

# ✅ PYTHONPATH を Airflow 全体に適用
ENV PYTHONPATH=/noctria_kingdom/airflow_docker

# ✅ 依存ライブラリをコピー（Airflow起動時に必要なAIモジュール群）
COPY requirements.txt /requirements.txt

# ✅ torch（CPU版）および transformers など LLM関連ライブラリをインストール
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
        torch==2.2.2+cpu \
        --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
        transformers \
        accelerate \
        sentencepiece \
        bitsandbytes==0.42.0 \
        huggingface-hub \
        einops \
        peft && \
    pip install --no-cache-dir -r /requirements.txt
