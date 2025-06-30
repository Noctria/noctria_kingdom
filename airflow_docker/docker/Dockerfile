# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile
# ベース: Apache Airflow 2.7.3 + Python 3.10
# ================================

FROM apache/airflow:2.7.3-python3.10

# 環境変数の設定（ログ非バッファリング / PYTHONPATH）
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/noctria_kingdom

# 🔹 パッケージリストと制約ファイルをコンテナにコピー
COPY airflow_docker/docker/requirements_airflow.txt /requirements_airflow.txt
COPY airflow_docker/docker/requirements_extra.txt /requirements_extra.txt
COPY airflow_docker/docker/constraints.txt /tmp/constraints.txt

# 🔹 Airflow本体や周辺ユーティリティのみ先にインストール（制約付き）
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements_airflow.txt --constraint /tmp/constraints.txt

# 🔹 強化学習・深層学習・外部依存など制約外のパッケージを別途インストール
RUN pip install --no-cache-dir -r /requirements_extra.txt
