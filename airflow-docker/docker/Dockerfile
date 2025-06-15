FROM apache/airflow:2.9.1-python3.10

USER root
# 必要なシステムパッケージ（scikit-learnやlxmlなどに必要）
RUN apt-get update && apt-get install -y \
    gcc g++ libpq-dev build-essential \
    libxml2-dev libxslt1-dev zlib1g-dev

USER airflow

# torch は pip install に特殊オプションが必要なため Dockerfileで個別に
COPY requirements.airflow.txt /requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        torch==2.2.2+cpu \
        --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /requirements.txt
