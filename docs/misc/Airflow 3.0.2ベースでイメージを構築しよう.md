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

- **51ddf2a** 2025-08-15T19:53:46+09:00 — docs: AUTODOCブロック挿入および本文更新 (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/00_index/00-INDEX.md.bak`
  - `docs/README.md`
  - `docs/README.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md`
  - `docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md`
  - `docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/03_entities_schemas.md`
  - `docs/_partials/apis/Do-Layer-Contract/03_entities_schemas.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/04_order_request.md`
  - `docs/_partials/apis/Do-Layer-Contract/04_order_request.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/05_exec_result.md`
  - `docs/_partials/apis/Do-Layer-Contract/05_exec_result.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/06_audit_order.md`
  - `docs/_partials/apis/Do-Layer-Contract/06_audit_order.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md`
  - `docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md`
  - `docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md.bak`
- **7111b30** 2025-08-15T19:38:34+09:00 — docs: AUTODOCブロック挿入および本文更新 (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/00_index/00-INDEX.md.bak`
  - `docs/README.md`
  - `docs/README.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md`
  - `docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md`
  - `docs/_partials/apis/Do-Layer-Contract/03_entities_schemas.md`
  - `docs/_partials/apis/Do-Layer-Contract/04_order_request.md`
  - `docs/_partials/apis/Do-Layer-Contract/05_exec_result.md`
  - `docs/_partials/apis/Do-Layer-Contract/06_audit_order.md`
  - `docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md`
  - `docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md`
  - `docs/_partials/apis/Do-Layer-Contract/09_error_codes.md`
  - `docs/_partials/apis/Do-Layer-Contract/10_samples_min.md`
  - `docs/_partials/apis/Do-Layer-Contract/11_contract_tests.md`
  - `docs/_partials/apis/Do-Layer-Contract/12_changelog.md`
  - `docs/adrs/ADRs.md`
  - `docs/adrs/ADRs.md.bak`
  - `docs/apis/Do-Layer-Contract.md`
  - `docs/apis/Do-Layer-Contract.md.bak`
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
