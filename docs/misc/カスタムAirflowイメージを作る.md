もちろんです！以下に、GitHub向けに見やすく整形したMarkdownファイル内容をまとめました🚀✨

markdown
コピーする
編集する
# airflow-docker/Dockerfile （カスタムDockerfile完全版）

Noctria Kingdom の Airflow 環境を拡張し、必要なパッケージを自動的にインストールするためのカスタム Dockerfile です。  
`gym`, `optuna`, `shimmy`, `tensorboard` を追加して、手動インストールの手間を省きます！

---

## 📁 ファイル構成

以下のファイルを `airflow-docker/` に置きます。

```plaintext
airflow-docker/
├── docker-compose.yaml
├── Dockerfile
├── dags/
├── logs/
├── scripts/
├── data/
├── core/
📝 Dockerfile 内容
Dockerfile
コピーする
編集する
FROM apache/airflow:2.8.0

# rootユーザーに切り替え
USER root

# 必要に応じてOSレベルのツールもインストールできます
# RUN apt-get update && apt-get install -y nano vim

# Pythonパッケージをまとめてインストール
RUN pip install --no-cache-dir \
    gym \
    optuna \
    shimmy>=2.0 \
    tensorboard \
    && pip cache purge

# airflowユーザーに戻す
USER airflow
🚀 docker-compose.yaml の修正例
airflow-webserver サービスに以下を追加します。

yaml
コピーする
編集する
  airflow-webserver:
    build: .
    image: custom_airflow:latest
    ports:
      - "8080:8080"
      - "6006:6006"  # TensorBoard用
    ...
他のサービス（例: airflow-scheduler, airflow-init）にも build: . を追加すると、同じカスタムイメージを使えます。

💡 ビルド＆起動手順
1️⃣ カレントディレクトリを airflow-docker に移動

bash
コピーする
編集する
cd /opt/airflow-main/airflow-docker
2️⃣ カスタムイメージをビルドしながら起動

bash
コピーする
編集する
docker compose down
docker compose up --build -d
🎯 効果
✅ これで Airflow 環境内に gym, optuna, shimmy, tensorboard が自動的にインストールされます！
✅ 以後、手動で pip install する必要はありません。
<!-- AUTODOC:BEGIN mode=git_log path_globs=docs/misc/*.md title="Misc 文書更新履歴（最近30）" limit=30 since=2025-08-01 -->
### Misc 文書更新履歴（最近30）

_変更は見つかりませんでした。_
<!-- AUTODOC:END -->
