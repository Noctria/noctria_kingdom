# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile
# ベース: Apache Airflow 2.7.3 + Python 3.10
# ================================

FROM apache/airflow:2.7.3-python3.10

# 環境変数（ログ強度やPYTHONPATHの調整など）
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/noctria_kingdom

# パッケージリストと制約ファイルをコンテナにコピー
COPY requirements.txt /requirements.txt
COPY constraints.txt /constraints.txt

# pipパッケージをインストール（Airflow 2.7.3 + constraints対応）
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements.txt --constraint /constraints.txt
