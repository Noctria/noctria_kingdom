✅ 結論：Airflow 3.0.2ベースでイメージを構築しよう

apache/airflow:3.0.2-python3.12 をベースにするのがベスト。

事前に依存関係を解決した requirements.txt を用意しておく。

Dockerfile 内で pip install で一括インストール。Airflow自身も明示的にインストールすることで、バージョンの自動ダウングレードなどを防ぐ。

コンテナ起動時に余計な pip install をしない ことで、再構築の手間を減らす。

💡 例：日本語コメント付きのDockerfile

dockerfile
コピーする
編集する
# ✅ Airflow 3.0.2 + Python3.12ベースイメージ
FROM apache/airflow:3.0.2-python3.12

# ✅ 必要なシステムパッケージのインストール
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        cmake \
        python3-dev \
        zlib1g-dev \
        libbz2-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ✅ 依存性を解決済みの requirements.txt を先にコピー
COPY requirements.txt /requirements.txt

# ✅ Airflow本体（バージョン固定）とその他の依存ライブラリをインストール
RUN pip install --no-cache-dir "apache-airflow==3.0.2" \
    && pip install --no-cache-dir -r /requirements.txt

# ✅ airflowユーザーに戻す
USER airflow
🔧 ビルド手順例

bash
コピーする
編集する
docker compose build --no-cache
docker compose up -d
🪄 ポイントまとめ

すべての Python パッケージのバージョンは requirements.txt に明記しておく。

Airflow公式ドキュメントの推奨手順（https://airflow.apache.org/docs/docker-stack/index.html） に準拠。

コンテナ起動時に pip install は一切走らない ようにDockerfileを組むのがベストプラクティス。

これで、環境構築がスムーズになり、再ビルド時の時間も短縮できますよ！
他に質問があれば、どんどん聞いてくださいね 🙂
<!-- AUTODOC:BEGIN mode=git_log path_globs=docs/misc/*.md title="Misc 文書更新履歴（最近30）" limit=30 since=2025-08-01 -->
### Misc 文書更新履歴（最近30）

_変更は見つかりませんでした。_
<!-- AUTODOC:END -->
