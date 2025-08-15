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
<!-- AUTODOC:BEGIN mode=git_log path_globs=docs/misc/*.md title="Misc 文書更新履歴（最近30）" limit=30 since=2025-08-01 -->
### Misc 文書更新履歴（最近30）

- **30ae379** 2025-08-15T18:55:06+09:00 — 📄 AutoDoc: update docs from index (by Veritas Machina)
  - `action`
  - `data/decisions/ledger.csv`
  - `data/models/prometheus/PPO/obs8/latest`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:18:10+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:18:10+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:19:41+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:19:41+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:22:19+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:22:19+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:33:11+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:33:11+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T15:44:05+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T15:44:05+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:20:12.935706+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:20:12.935706+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:21:36.023694+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:21:36.023694+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:27:02.701382+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:27:02.701382+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T17:21:59.539332+00:00/metadata.json`
<!-- AUTODOC:END -->
