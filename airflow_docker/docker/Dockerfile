# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile (v3.0)
# ================================

FROM apache/airflow:2.7.3-python3.10

# 🔹 ログ非バッファ化 / 統一ルートパス
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/airflow \
    AIRFLOW_HOME=/opt/airflow

# 🔹 作業ディレクトリ
WORKDIR ${AIRFLOW_HOME}

# 🔹 要求パッケージのコピー（build context: airflow_docker/docker/）
COPY requirements_airflow.txt /requirements_airflow.txt
COPY requirements_extra.txt /requirements_extra.txt
COPY constraints.txt /tmp/constraints.txt

# 🔹 Airflow本体 + 基本依存パッケージ
RUN set -ex \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements_airflow.txt --constraint /tmp/constraints.txt

# 🔹 外部依存（制約に入れない重い・GPU系など）
RUN pip install --no-cache-dir -r /requirements_extra.txt

# 🔹 ビルド後の軽量化（任意）
RUN rm -rf /root/.cache /tmp/constraints.txt
