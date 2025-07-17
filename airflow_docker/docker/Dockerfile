# Noctria Kingdom Airflow Image (v2.5)
# ✅ 修正: ベースイメージをPython 3.11対応のバージョンに変更
FROM apache/airflow:2.9.2-python3.11

# rootユーザーに切り替えて、ファイルのコピーと権限設定を行う
USER root

COPY ./airflow_docker/docker/entrypoint-webserver.sh /entrypoint-webserver.sh
RUN chmod +x /entrypoint-webserver.sh
RUN chown airflow /entrypoint-webserver.sh

# 再びairflowユーザーに戻して、以降の処理を続ける
USER airflow

# Pythonの依存関係をインストール
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
