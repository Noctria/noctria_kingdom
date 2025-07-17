# Noctria Kingdom Airflow Image (v2.4)
FROM apache/airflow:2.8.1-python3.10

# rootユーザーに切り替えて、ファイルのコピーと権限設定を行う
USER root

COPY ./airflow_docker/docker/entrypoint-webserver.sh /entrypoint-webserver.sh
RUN chmod +x /entrypoint-webserver.sh
# ✅ 修正: 所有者の指定をユーザー名のみに変更
RUN chown airflow /entrypoint-webserver.sh

# 再びairflowユーザーに戻して、以降の処理を続ける
USER airflow

# Pythonの依存関係をインストール
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
