
🟩 次回起動手順
✅ 1️⃣ 必要なディレクトリに移動
bash
コピーする
編集する
cd /mnt/e/noctria-kingdom-main/airflow-docker
（docker-compose.yaml がある場所）

✅ 2️⃣ Airflowを起動
bash
コピーする
編集する
docker compose up
これで WebUI（http://localhost:8080） にアクセス可能！
ブラウザでログインすれば、また王国が動き出すよ👑✨

✅ スケジューラーのdockerに入るためのコマンド
AireFlowディレクトリに移動して
docker exec -it airflow-docker-airflow-scheduler-1 /bin/bash

中で以下を実行し、gym と core の存在 を確認
python3 -c "import gym; print(gym.__file__)"
ls /opt/airflow/core


🟩 補足: バックグラウンドで立ち上げる場合
bash
コピーする
編集する
docker compose up -d
（-d は detached モード → 端末を占有しない）

🟩 停止する場合
bash
コピーする
編集する
docker compose down
これでAirflowとそのコンテナ群をまとめて停止可能。

🟩 現在のコンテナ状況を確認
bash
コピーする
編集する
docker compose ps
🟩 まとめ
✅ 起動:

bash
コピーする
編集する
cd /mnt/e/noctria-kingdom-main/airflow-docker  
docker compose up
✅ 停止:

nginx
コピーする
編集する
docker compose down
✅ ステータス確認:

nginx
コピーする
編集する
docker compose ps
