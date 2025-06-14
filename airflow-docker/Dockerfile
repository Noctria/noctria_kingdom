# 📦 ベースイメージ（Airflow 2.9.1 + Python 3.10）
FROM apache/airflow:2.9.1-python3.10

# 🛠 OSレベルの依存関係をインストール（ML系 + build必須系）
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

# 🧪 Airflowの追加プロバイダーを明示的にインストール（fab認証エラー対策）
# さらに、CeleryExecutor用の Redis/Postgres Providerも追加
USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r /requirements.txt \
 && pip install --no-cache-dir \
    apache-airflow-providers-flask-appbuilder \
    apache-airflow-providers-redis \
    apache-airflow-providers-postgres
