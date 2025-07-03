# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile
# ベース: Apache Airflow 2.7.3 + Python 3.10
# ================================

FROM apache/airflow:2.7.3-python3.10

# 🔹 環境変数の設定（ログ非バッファリング / パス / Airflow構成ルート）
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/noctria_kingdom \
    AIRFLOW_HOME=/noctria_kingdom/airflow_docker

# 🔹 作業ディレクトリ（CLI実行の基準ディレクトリ）
WORKDIR ${AIRFLOW_HOME}

# 🔹 パッケージリストと制約ファイルをコンテナにコピー
COPY airflow_docker/docker/requirements_airflow.txt /requirements_airflow.txt
COPY airflow_docker/docker/requirements_extra.txt /requirements_extra.txt
COPY airflow_docker/docker/constraints.txt /tmp/constraints.txt

# 🔹 Airflow本体や周辺ユーティリティを先にインストール
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements_airflow.txt --constraint /tmp/constraints.txt

# 🔹 深層学習・強化学習・外部系など制約外パッケージを後から
RUN pip install --no-cache-dir -r /requirements_extra.txt
