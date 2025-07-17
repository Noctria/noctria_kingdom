# Noctria Kingdom Airflow Image (v2.1)
FROM apache/airflow:2.8.1-python3.10

# ✅ 修正: rootユーザーに切り替えて、ファイルのコピーと権限設定を行う
USER root

# Webサーバー用の起動スクリプトをコンテナ内にコピー
COPY ./docker/entrypoint-webserver.sh /entrypoint-webserver.sh
# コピーしたスクリプトに実行権限を付与
RUN chmod +x /entrypoint-webserver.sh
# ✅ 追加: スクリプトの所有者をairflowユーザーに変更し、後の操作で問題が起きないようにする
RUN chown airflow:airflow /entrypoint-webserver.sh

# ✅ 修正: 再びairflowユーザーに戻して、以降の処理を続ける
USER airflow

# Pythonの依存関係をインストール
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
