FROM apache/airflow:2.8.0

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

# ✅ 先にrequirements.txtだけコピーしてキャッシュ化
COPY requirements.txt /requirements.txt

# ✅ 依存パッケージをまとめてインストール（キャッシュ活用できる形に）
RUN /usr/local/bin/pip install --no-cache-dir -r /requirements.txt

USER airflow
