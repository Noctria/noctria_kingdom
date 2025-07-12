# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile (v3.3)
# ================================

FROM apache/airflow:2.7.3-python3.10

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/airflow \
    AIRFLOW_HOME=/opt/airflow

WORKDIR ${AIRFLOW_HOME}

USER root
RUN apt-get update && apt-get install -y git && apt-get clean
USER airflow

COPY docker/requirements_airflow.txt /requirements_airflow.txt
COPY docker/requirements_extra.txt /requirements_extra.txt
COPY docker/constraints.txt /tmp/constraints.txt

RUN set -ex \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements_airflow.txt --constraint /tmp/constraints.txt

RUN pip install --no-cache-dir -r /requirements_extra.txt

# ✅ GitHub経由ではなく PyPIから sb3-contrib を指定バージョンでインストール
RUN pip uninstall -y sb3-contrib stable-baselines3 || true \
 && pip install --no-cache-dir sb3-contrib==2.2.1 stable-baselines3==2.2.1

RUN rm -f /tmp/constraints.txt || true
