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

# 依存パッケージをインストール
# * requirements_* に未記載でも最低限の最適化依存が入るよう fallback を併用
RUN set -eux; \
    pip install --no-cache-dir -r /requirements.txt; \
    pip install --no-cache-dir -r /requirements_extra.txt || true; \
    # フォールバック（未記載だった場合のみ解決される想定）
    pip install --no-cache-dir \
      optuna \
      gymnasium \
      stable-baselines3 \
    ; \
    # CPU版 PyTorch（GPU不要な想定。GPUを使うならcompose側で差し替え）
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu || true

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
    mkdir -p /opt/airflow/dags; \
    mkdir -p /opt/airflow/src; \
    mkdir -p /opt/airflow/logs; \
    mkdir -p /opt/airflow/plugins

# 以降は docker-compose 側で:
#   - ./airflow_docker/dags:/opt/airflow/dags
#   - ./src:/opt/airflow/src
#   - ./airflow_docker/logs:/opt/airflow/logs
# …などのマウントを推奨
