FROM apache/airflow:2.9.1-python3.10

USER root

# ✅ システムパッケージのインストール（scikit-learn, lxml, pytorchなどに必要）
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

# ✅ torch 導入（CPU版）＋ requirements.airflow.txt のインストール
COPY requirements.airflow.txt /requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        torch==2.2.2+cpu \
        --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /requirements.txt
