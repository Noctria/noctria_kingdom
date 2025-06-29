# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile
# ベース: Apache Airflow 2.9.1 + Python 3.10
# ================================

FROM apache/airflow:2.9.1-python3.10

# 環境変数（ログ強度やPYTHONPATHの調整など）
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/noctria_kingdom

# パッケージリストをコンテナにコピー
COPY requirements.txt /requirements.txt

# pipパッケージをインストール（Airflow 2.9.1対応）
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements.txt
