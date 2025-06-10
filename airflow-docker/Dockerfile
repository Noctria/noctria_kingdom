# ベースはAirflow公式イメージ
FROM apache/airflow:2.8.0

# rootユーザーに切り替え
USER root

# 必要なシステムパッケージをインストール（例: gitなど）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# airflow-docker/requirements.txt をコピー
COPY requirements.txt /requirements.txt

# pipで追加パッケージをインストール
RUN pip install --no-cache-dir -r /requirements.txt

# （必要な場合）bashrc のカスタマイズ
# COPY bashrc /etc/bash.bashrc
# RUN chmod a+rwx /etc/bash.bashrc

# airflowユーザーに戻す
USER airflow
