FROM apache/airflow:2.9.1-python3.10  # ✅ Python 3.10 確保

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

# ✅ pip & TensorFlow（2.14.0）インストール
RUN pip install --upgrade pip
RUN pip install tensorflow==2.14.0

USER airflow
