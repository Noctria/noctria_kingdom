# ✅ Airflow 3.0.2 + Python3.12ベースイメージ
FROM apache/airflow:3.0.2-python3.12

# ✅ 必要なシステムパッケージのインストール
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

# ✅ 依存性を解決済みの requirements.txt を先にコピー
COPY requirements.txt /requirements.txt

# ✅ Airflow本体（バージョン固定）とその他の依存ライブラリをインストール
RUN pip install --no-cache-dir "apache-airflow==3.0.2" \
    && pip install --no-cache-dir -r /requirements.txt

# ✅ airflowユーザーに戻す
USER airflow
