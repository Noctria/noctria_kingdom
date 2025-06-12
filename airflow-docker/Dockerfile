FROM apache/airflow:2.9.1-python3.10

# ✅ OSパッケージ（TensorFlowやSB3、Gym系に必要）
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libatlas-base-dev \
    python3-dev \
    libhdf5-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
 && rm -rf /var/lib/apt/lists/*

# ✅ airflowユーザーでPythonパッケージをインストール
USER airflow
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt
