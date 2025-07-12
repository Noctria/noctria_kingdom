# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile (v3.3)
# ================================

FROM apache/airflow:2.7.3-python3.10

# ✅ 環境変数定義
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/airflow \
    AIRFLOW_HOME=/opt/airflow

WORKDIR ${AIRFLOW_HOME}

# ✅ Gitコマンドの追加（sb3等の開発環境対応）
USER root
RUN apt-get update && apt-get install -y git && apt-get clean
USER airflow

# ✅ 依存ファイルコピー
COPY docker/requirements_airflow.txt /requirements_airflow.txt
COPY docker/requirements_extra.txt /requirements_extra.txt
COPY docker/constraints.txt /tmp/constraints.txt

# ✅ Airflow必須要件インストール（constraintあり）
RUN set -ex \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements_airflow.txt --constraint /tmp/constraints.txt

# ✅ 追加依存のインストール
RUN pip install --no-cache-dir -r /requirements_extra.txt

# ✅ SB3関連（GitHub経由を避けて PyPI から特定バージョン）
RUN pip uninstall -y sb3-contrib stable-baselines3 || true \
 && pip install --no-cache-dir stable-baselines3==2.2.1 sb3-contrib==2.2.1

# ✅ 不要ファイルの削除
RUN rm -f /tmp/constraints.txt || true
