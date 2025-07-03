# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile (v2.1)
# ================================

FROM apache/airflow:2.7.3-python3.10

# 🔹 ログ非バッファ化 / 統一ルート
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/airflow \
    AIRFLOW_HOME=/opt/airflow

# 🔹 作業ディレクトリ
WORKDIR ${AIRFLOW_HOME}

# 🔹 パッケージファイルのコピー（build contextが airflow_docker/ の場合）
COPY docker/requirements_airflow.txt /requirements_airflow.txt
COPY docker/requirements_extra.txt /requirements_extra.txt
COPY docker/constraints.txt /tmp/constraints.txt

# 🔹 Airflow 本体 + 周辺パッケージ
RUN set -ex \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements_airflow.txt --constraint /tmp/constraints.txt

# 🔹 外部・重いパッケージ（制約外）
RUN pip install --no-cache-dir -r /requirements_extra.txt
