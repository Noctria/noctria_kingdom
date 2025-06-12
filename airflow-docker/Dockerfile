FROM apache/airflow:slim-3.0.2-python3.9

# rootユーザーで一時的に必要なものを入れる
USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git build-essential cmake \
        python3-dev zlib1g-dev libbz2-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt

# airflowユーザーに切り替えてから pip install するのが公式推奨
USER airflow

RUN pip install --no-cache-dir "apache-airflow==3.0.2" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.0.2/constraints-3.9.txt" && \
    pip install --no-cache-dir -r /requirements.txt && \
    pip install --no-cache-dir tensorflow==2.19.0 yfinance==0.2.62
