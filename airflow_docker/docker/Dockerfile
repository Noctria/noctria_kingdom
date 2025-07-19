# ===========================================
# Noctria Kingdom - Airflowカスタムイメージ
# ベース: Apache Airflow 2.9.2 + Python 3.11
# ===========================================

FROM apache/airflow:2.9.2-python3.11

# 追加で必要なOSパッケージをインストール（git以外に必要ならここで追記）
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Python依存ファイルをイメージにコピー（build contextから相対パス！）
COPY airflow_docker/requirements.txt /requirements.txt

# 依存パッケージをインストール
RUN pip install --no-cache-dir -r /requirements.txt

# -- 追加：他にもrequirements_extra.txtなどを使いたい場合はここでCOPY・インストール可 --
# COPY airflow_docker/requirements_extra.txt /requirements_extra.txt
# RUN pip install --no-cache-dir -r /requirements_extra.txt
