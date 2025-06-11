FROM apache/airflow:2.8.0

# rootユーザーで追加パッケージをインストール
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtをコピー
COPY requirements.txt /requirements.txt

# ✅ rootユーザーでpip install（システム全体にインストールされる！）
RUN python -m pip install --no-cache-dir -r /requirements.txt \
    && python -m pip install --no-cache-dir statsmodels blosc2

# airflowユーザーに切り替え
USER airflow
