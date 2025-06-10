🚀 DockerでTensorBoardを起動する手順  
1️⃣ コンテナ内に入る  
Airflowのコンテナにアクセスします（例としてwebserverコンテナを使用）:

bash
コピーする
編集する
docker compose exec airflow-webserver bash
2️⃣ TensorBoardを起動する
コンテナ内で以下のコマンドを実行します。
--logdir にはPPO学習時に指定したTensorBoardログのパスを入力します（例: /opt/airflow/logs/ppo_tensorboard_logs）。

bash
コピーする
編集する
tensorboard --logdir /opt/airflow/logs/ppo_tensorboard_logs --host 0.0.0.0 --port 6006
3️⃣ ブラウザでアクセスする
ホストPCのブラウザで以下のURLにアクセスしてTensorBoardを開きます:

arduino
コピーする
編集する
http://localhost:6006
✅ ポイント
--host 0.0.0.0: 外部からも接続可能にする設定です（ローカルホストにバインド）。

--port 6006: デフォルトのTensorBoardポートです。競合がある場合は別ポートを指定できます。

Airflowコンテナに tensorboard がインストールされていない場合は、Dockerfileで事前にインストールしておく必要があります（RUN pip install tensorboard）。
