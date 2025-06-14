# ベースイメージ
FROM apache/airflow:2.9.1-python3.10

# OSライブラリ
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libatlas-base-dev \
    python3-dev \
    libhdf5-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
 && rm -rf /var/lib/apt/lists/*

# Pythonライブラリ
USER airflow
COPY requirements.txt /requirements.txt

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r /requirements.txt \
 && pip install --no-cache-dir \
     apache-airflow-providers-redis \
     apache-airflow-providers-postgres
