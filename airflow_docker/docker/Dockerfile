# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile
# ベース: Airflow 2.7.3 + Python 3.10
# ================================

FROM apache/airflow:2.7.3-python3.10

# 作業ディレクトリ
WORKDIR /opt/airflow

# 環境変数
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/noctria_kingdom \
    AIRFLOW_HOME=/opt/airflow

# requirements + constraints ファイル追加
COPY requirements.txt /requirements.txt
ADD https://raw.githubusercontent.com/apache/airflow/constraints-2.7.3/constraints-3.10.txt /constraints.txt

# 依存関係インストール
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /requirements.txt --constraint /constraints.txt
