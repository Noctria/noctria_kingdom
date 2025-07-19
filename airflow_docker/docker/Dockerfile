# ベースイメージを指定
FROM apache/airflow:2.9.2-python3.11

# パッケージインストールとキャッシュ削除を1つのRUN命令で実行し、イメージサイズを削減
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
USER airflow

# 依存関係ファイルをコンテナにコピー
# COPYのパスはdocker-compose.yamlのbuild contextからの相対パスになります
# airflow_docker/requirements.txtに配置した場合
COPY airflow_docker/requirements.txt /requirements.txt

# requirements.txtから全てのPythonパッケージを一度にインストール
RUN pip install --no-cache-dir -r /requirements.txt
