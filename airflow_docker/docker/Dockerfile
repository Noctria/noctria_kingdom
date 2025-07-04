# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile (v3.0)
# ================================

FROM apache/airflow:2.7.3-python3.10

# 🔹 環境変数（ログ非バッファ・Airflowルート統一）
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/airflow \
    AIRFLOW_HOME=/opt/airflow

# 🔹 作業ディレクトリ
WORKDIR ${AIRFLOW_HOME}

# 🔹 パッケージ要求ファイルのコピー（build context: airflow_docker/docker/）
COPY requirements_airflow.txt /requirements_airflow.txt
COPY requirements_extra.txt /requirements_extra.txt
COPY constraints.txt /tmp/constraints.txt

# 🔹 Airflow + 基本依存パッケージのインストール
RUN set -ex \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements_airflow.txt --constraint /tmp/constraints.txt

# 🔹 外部依存パッケージのインストール（重いもの、制約外）
RUN pip install --no-cache-dir -r /requirements_extra.txt

# 🔹 ビルド後のキャッシュ削除（失敗しても継続）
RUN rm -f /tmp/constraints.txt || true
