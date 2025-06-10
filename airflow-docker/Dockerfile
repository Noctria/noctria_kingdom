FROM apache/airflow:2.8.0

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt

# airflowユーザーに切り替えて pip install
USER airflow
RUN pip install --no-cache-dir -r /requirements.txt

# airflowユーザーでコンテナ起動（デフォルト）
