# ================================
# 🌪 Noctria Kingdom: Airflow Dockerfile (v3.4)
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

# ✅ 必要なファイルをコピー（依存定義）
COPY docker/requirements_airflow.txt /requirements_airflow.txt
COPY docker/requirements_extra.txt /requirements_extra.txt
COPY docker/constraints.txt /tmp/constraints.txt

# ✅ Airflowの公式推奨に基づいた依存インストール
RUN set -ex \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r /requirements_airflow.txt --constraint /tmp/constraints.txt

# ✅ 追加依存パッケージ
RUN pip install --no-cache-dir -r /requirements_extra.txt

# ✅ SB3関連（GitHubではなくPyPIからインストール）
RUN pip uninstall -y sb3-contrib stable-baselines3 || true \
 && pip install --no-cache-dir stable-baselines3==2.2.1 sb3-contrib==2.2.1

# ✅ 管理者アカウント作成用スクリプトのコピー（ツール群）
COPY tools/create_admin_user.py /opt/airflow/tools/create_admin_user.py
COPY tools/entrypoint.sh /opt/airflow/tools/entrypoint.sh

# ✅ Entrypointスクリプトに実行権限を付与
RUN chmod +x /opt/airflow/tools/entrypoint.sh

# ✅ Entrypointを上書き（Airflow標準→独自スクリプト）
ENTRYPOINT ["/opt/airflow/tools/entrypoint.sh"]

# ✅ 不要ファイルのクリーンアップ
RUN rm -f /tmp/constraints.txt || true
