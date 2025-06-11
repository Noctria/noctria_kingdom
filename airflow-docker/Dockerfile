FROM apache/airflow:2.8.0

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \   # ← これを追加！
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt

# ✅ /usr/local/bin/pip でシステム全体にインストール
RUN /usr/local/bin/pip install --no-cache-dir -r /requirements.txt \
    && /usr/local/bin/pip install --no-cache-dir statsmodels blosc2

USER airflow
