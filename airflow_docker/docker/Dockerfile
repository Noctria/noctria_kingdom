# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile (v3.2)
# ================================

FROM apache/airflow:2.7.3-python3.10

# 🔹 環境変数（ログ非バッファ・Airflowルート統一）
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/airflow \
    AIRFLOW_HOME=/opt/airflow

# 🔹 作業ディレクトリ
WORKDIR ${AIRFLOW_HOME}

# ================================
# 🔧 必要なシステムパッケージ（Gitなど）
# ================================
USER root
RUN apt-get update && apt-get install -y git && apt-get clean
USER airflow

# ================================
# 📦 パッケージ要件ファイルのコピー
# build context: airflow_docker/docker/
# ================================
COPY docker/requirements_airflow.txt /requirements_airflow.txt
COPY docker/requirements_extra.txt /requirements_extra.txt
COPY docker/constraints.txt /tmp/constraints.txt

# ================================
# 🛠 Airflow本体 + 依存パッケージ
# ================================
RUN set -ex \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements_airflow.txt --constraint /tmp/constraints.txt

# ================================
# 🧩 追加の通常パッケージ
# ================================
RUN pip install --no-cache-dir -r /requirements_extra.txt

# ================================
# ✅ sb3-contrib & stable-baselines3（GitHubから）
# - optuna_callback を含む TrialEvalCallback対応
# ================================
RUN pip uninstall -y sb3-contrib stable-baselines3 || true \
 && pip install --no-cache-dir git+https://github.com/DLR-RM/stable-baselines3-contrib.git@v2.2.0

# ================================
# 🧹 一時ファイルクリーンアップ
# ================================
RUN rm -f /tmp/constraints.txt || true
