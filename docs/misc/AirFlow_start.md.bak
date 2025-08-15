
🟩 次回起動手順
✅ 1️⃣ 必要なディレクトリに移動
bash
コピーする
編集する
cd /opt/airflow-main/airflow-docker
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
cd /opt/airflow-main/airflow-docker  
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
