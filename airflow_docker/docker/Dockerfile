# Noctria Kingdom Airflow Image (v2.3)
FROM apache/airflow:2.8.1-python3.10

# rootユーザーに切り替えて、ファイルのコピーと権限設定を行う
USER root

# ✅ 修正: 新しいビルドコンテキスト（プロジェクトルート）からの正しい相対パスに修正
COPY ./airflow_docker/docker/entrypoint-webserver.sh /entrypoint-webserver.sh
RUN chmod +x /entrypoint-webserver.sh
RUN chown airflow:airflow /entrypoint-webserver.sh

# 再びairflowユーザーに戻して、以降の処理を続ける
USER airflow

# Pythonの依存関係をインストール
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
