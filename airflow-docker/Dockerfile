FROM apache/airflow:3.0.2-python3.9

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      git build-essential cmake python3-dev \
      zlib1g-dev libbz2-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

USER airflow
