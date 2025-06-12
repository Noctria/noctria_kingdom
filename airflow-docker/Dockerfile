FROM apache/airflow:2.8.2-python3.9

# rootユーザーで apt パッケージなどをインストール
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 必要なPythonパッケージを airflow ユーザーでインストール
USER airflow

COPY requirements.txt /requirements.txt

RUN pip install --no-cache-dir --constraint \
    https://raw.githubusercontent.com/apache/airflow/constraints-2.8.2/constraints-3.9.txt \
    apache-airflow==2.8.2 && \
    pip install --no-cache-dir -r /requirements.txt
