# ===========================================
# Noctria Kingdom - Airflowカスタムイメージ
# ベース: Apache Airflow 2.9.2 + Python 3.11
# ===========================================

FROM apache/airflow:2.9.2-python3.11

# ---------- OSパッケージ ----------
USER root
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      git \
      # RL環境でたまに必要になる軽量依存（必要最低限）
      swig \
      ffmpeg \
      libgl1 \
      libglib2.0-0 \
    ; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

USER airflow

# ---------- Python 依存関係 ----------
# 事前に requirements をコピーしてインストール
# * requirements.txt: Airflow プラグイン・社内共通依存など
# * requirements_extra.txt: 学習/最適化系（Optuna/SB3/Gymnasium/PyTorchなど）を想定
COPY airflow_docker/requirements.txt /requirements.txt
COPY airflow_docker/requirements_extra.txt /requirements_extra.txt

# pip のノイズ・キャッシュ抑制
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
# TensorFlow 等の冗長ログ抑制（必要に応じて compose 側で上書き可）
ENV TF_CPP_MIN_LOG_LEVEL=2

# 依存パッケージをインストール
# * requirements_* に未記載でも最低限の最適化依存が入るよう fallback を併用
RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /requirements.txt && \
    pip install --no-cache-dir -r /requirements_extra.txt || true && \
    # 旧 gym は SB3 2.x では不要（警告の原因）。存在しても削除
    pip uninstall -y gym || true && \
    # 必要最低限の RL 依存を明示（SB3 2.x 前提）
    pip install --no-cache-dir \
      "gymnasium>=0.29" \
      "stable-baselines3>=2.2" \
      "sb3-contrib>=2.2" && \
    # CPU 版 PyTorch（GPU を使う場合は compose 側で差し替え）
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu || true && \
    pip check || true

# ---------- 環境変数（ランタイムでも上書き可） ----------
# src の絶対インポートを保証
ENV PYTHONPATH="/opt/airflow/src:/opt/airflow:${PYTHONPATH}"

# Optuna RDB ストレージの既定（compose/env で上書き推奨）
ENV OPTUNA_STORAGE="postgresql+psycopg2://airflow:airflow@noctria_postgres:5432/airflow"

# Airflow 設定の軽微な既定
ENV AIRFLOW__CORE__LOAD_EXAMPLES="False"

# ---------- ディレクトリ作成（実運用はボリュームでマウント想定） ----------
# * コピーはせず、マウント受け側の空ディレクトリのみ用意
RUN set -eux; \
    mkdir -p /opt/airflow/dags && \
    mkdir -p /opt/airflow/src && \
    mkdir -p /opt/airflow/logs && \
    mkdir -p /opt/airflow/plugins

# 以降は docker-compose 側で:
#   - ./dags:/opt/airflow/dags
#   - ../src:/opt/airflow/src
#   - ../logs:/opt/airflow/logs
#   - ./plugins:/opt/airflow/plugins
#   - ../data:/opt/airflow/data
# …などのマウントを推奨
