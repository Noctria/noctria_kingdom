# 📜 Noctria Kingdom プロジェクト INDEX（標準引き継ぎ用 / 2025-08-14 更新）

## 1. 目的
Noctria Kingdom の全体像・統治構造・役割分担・運用方針を明確化し、担当交代や並行開発時にもブレずに資産を維持・拡張できる状態を保つ。

---

## 2. プロジェクト全体像
Noctria Kingdom は、中央統治AI「King Noctria」を頂点に、複数の専門AI（臣下）が市場戦略の **Plan → Do → Check → Act** を自動実行する統治型金融AIシステム。

- **中央統治AI**
  - `src/core/king_noctria.py`
  - 臣下AIの提案を統合し、最終意思決定を下す。

- **臣下AI（代表）**
  | AI名 | ファイル | 役割 |
  |------|----------|------|
  | Aurus Singularis | `src/strategies/Aurus_Singularis.py` | 市場解析・総合戦略立案 |
  | Levia Tempest | `src/strategies/Levia_Tempest.py` | 高速スキャルピング |
  | Noctus Sentinella | `src/strategies/Noctus_Sentinella.py` | リスク評価・資本保護 |
  | Prometheus Oracle | `src/strategies/Prometheus_Oracle.py` | 中長期予測 |
  | Veritas | `src/veritas/` | 戦略生成・学習最適化 |
  | Hermes Cognitor | `src/hermes/` | 戦略説明・自然言語化 |

### 2.1 アーキテクチャ（概観）
```mermaid
flowchart LR
  subgraph User["User / Operator"]
    UI["GUI (FastAPI + Gunicorn)"]
  end

  subgraph Runtime["Runtime Layers"]
    KING["King Noctria (core)"]
    STRATS["Strategies (Aurus/Levia/Noctus/Prometheus/…)"]
    PLAN["Plan Layer (data/feature)"]
    EVAL["Check (evaluation/stats)"]
    ACT["Act (retrain/opt)"]
  end

  subgraph Infra["Infra"]
    AF["Airflow (webserver/scheduler)"]
    PG["PostgreSQL (Docker: pg-noctria)"]
    OBS["Observability Tables/Views"]
  end

  UI <-- REST/HTML --> KING
  KING <--> STRATS
  KING <--> PLAN
  KING <--> EVAL
  KING --> ACT
  AF --> KING
  AF --> STRATS
  AF --> PLAN
  AF --> EVAL
  AF --> ACT

  PLAN -.log.-> OBS
  STRATS -.log.-> OBS
  KING -.log.-> OBS
  UI <-- read --> OBS

  PG --- OBS
```

---

## 3. 統治レイヤー構造と PDCA

1. **中央統治レイヤ（最終決定）**
   - `src/core/king_noctria.py`
   - `airflow_docker/dags/noctria_kingdom_pdca_dag.py`
   - `airflow_docker/dags/noctria_kingdom_dag.py`

2. **PDCA**
   - **Plan**: データ収集〜特徴量生成（`src/plan_data/`）
   - **Do**: 戦略実行（`src/strategies/`）
   - **Check**: 評価・統計分析（`src/evaluation/`）
   - **Act**: 改善・再学習（`src/veritas/`, Airflow）

3. **Airflow 自動化**
   - 例: 学習 DAG `train_prometheus_obs8`
   - 例: 推論 DAG `oracle_prometheus_infer_dag.py`（新設時は設計意図を ADR に残す）

---

## 4. 可観測性（Observability）
- 実装: `src/plan_data/observability.py`
- **テーブル**
  - `obs_plan_runs`, `obs_infer_calls`, `obs_decisions`, `obs_exec_events`, `obs_alerts`
- **ビュー / マテビュー**
  - `obs_trace_timeline`, `obs_trace_latency`, `obs_latency_daily`
- **提供API（抜粋）**
  - `ensure_tables()`, `ensure_views()`, `ensure_views_and_mvs()`, `refresh_latency_daily()`
  - `log_plan_run()`, `log_infer_call()`, `log_decision()`, `log_exec_event()`, `log_alert()`

---

## 5. GUI 構造（FastAPI + Jinja2 / Gunicorn 運用）
- ルータ: `noctria_gui/routes/*`
- テンプレ: `noctria_gui/templates/*`（HUDスタイル）
- **主要ルート（最新）**
  | 機能 | ルート | テンプレート |
  |------|-------|--------------|
  | ダッシュボード | `/dashboard/` | `dashboard.html` |
  | **PDCAタイムライン** | `/pdca/timeline`（`?trace=<id>`で詳細、未指定で直近一覧） | `pdca_timeline.html` |
  | **レイテンシ日次** | `/pdca/latency/daily` | `pdca_latency_daily.html` |
  | 観測ビュー更新API | `POST /pdca/observability/refresh` | — |

> 旧リンクの **`/pdca/history`**, **`/strategies/compare`** は現行 UI と一致しない場合あり。本 INDEX を正とする。

---

## 6. ランタイム前提（環境サマリ）
| コンポーネント | 実行形態 | 環境/補足 |
|---|---|---|
| メインプログラム | venv | `venv_noctria` |
| GUI | venv + gunicorn（systemd 常駐）/ dev は uvicorn | `venv_gui` |
| Airflow | Docker | `noctria_airflow_webserver`, `noctria_airflow_scheduler` |
| PostgreSQL | Docker | コンテナ: `pg-noctria`（**ホスト公開 55432→5432**） |
| Docker ネットワーク | bridge + `airflow_docker_default` | **`pg-noctria` を `airflow_docker_default` に接続** |

---

## 7. Quick Start（開発者向け）

### 7.1 DB 初期化（ローカル）
```bash
# DSN は 55432（Docker の pg を WSL から叩く）
export NOCTRIA_OBS_PG_DSN="postgresql://noctria:noctria@127.0.0.1:55432/noctria_db"

python - <<'PY'
from src.plan_data.observability import ensure_tables, ensure_views_and_mvs, refresh_latency_daily
ensure_tables(); ensure_views_and_mvs(); refresh_latency_daily(concurrently=False)
print("OK: tables/views ensured + MV refreshed.")
PY
```

### 7.2 Airflow → Postgres 接続
```bash
# Airflow コンテナがいるネットワーク名を確認（例: airflow_docker_default）
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}" | grep -i airflow || true

# Postgres コンテナを Airflow のネットワークへ参加させる
docker network connect airflow_docker_default pg-noctria 2>/dev/null || true

# Airflow scheduler 内から接続作成（conn_id: noctria_obs_pg）
docker exec -it noctria_airflow_scheduler bash -lc '
  airflow connections delete noctria_obs_pg >/dev/null 2>&1 || true
  airflow connections add "noctria_obs_pg" \
    --conn-uri "postgresql://noctria:noctria@pg-noctria:5432/noctria_db"
  airflow connections get  "noctria_obs_pg"
'

# フックで疎通テスト
docker exec -it noctria_airflow_scheduler bash -lc 'python - <<PY
from airflow.providers.postgres.hooks.postgres import PostgresHook
hook = PostgresHook(postgres_conn_id="noctria_obs_pg")
with hook.get_conn() as conn, conn.cursor() as cur:
    cur.execute("select current_user, current_database()")
    print("OK:", cur.fetchone())
PY'
```

### 7.3 GUI（systemd 常駐）
**環境ファイル（LF / root:root / 644）** `/etc/default/noctria-gui`
```bash
sudo tee /etc/default/noctria-gui >/dev/null <<'ENV'
NOCTRIA_OBS_PG_DSN=postgresql://noctria:noctria@127.0.0.1:55432/noctria_db
NOCTRIA_GUI_PORT=8001
ENV
sudo chown root:root /etc/default/noctria-gui && sudo chmod 644 /etc/default/noctria-gui
```

**ユニット** `/etc/systemd/system/noctria_gui.service`  
（**ExecStart はシェルで環境変数展開**するのがポイント）
```ini
[Unit]
Description=Noctria GUI (Gunicorn + UvicornWorker)
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=noctria
Group=noctria
WorkingDirectory=/mnt/d/noctria_kingdom
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/mnt/d/noctria_kingdom
EnvironmentFile=/etc/default/noctria-gui

# シェル経由で ${NOCTRIA_GUI_PORT} を展開
ExecStart=/bin/sh -lc 'exec /mnt/d/noctria_kingdom/venv_gui/bin/gunicorn \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${NOCTRIA_GUI_PORT:-8001} \
  --access-logfile - \
  --error-logfile - \
  noctria_gui.main:app'

ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**起動 & 確認**
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now noctria_gui
# 反映確認（環境ファイルが読まれていること）
sudo systemctl show -p EnvironmentFiles -p Environment -p ExecStart noctria_gui
# LISTEN
ss -ltnp | grep ':8001' || sudo journalctl -u noctria_gui -n 80 --no-pager
# ヘルス
curl -sS http://127.0.0.1:${NOCTRIA_GUI_PORT:-8001}/healthz
```

---

## 8. トラブルシュート（抜粋）
- **Gunicorn が `$NOCTRIA_GUI_PORT` を不正扱い**
  - 原因: `ExecStart` がシェル経由でなく環境変数未展開
  - 対処: `/bin/sh -lc '…${NOCTRIA_GUI_PORT}…'` に修正し `daemon-reload` → 再起動

- **環境ファイルが読まれない/値がズレる**
  - CRLF 禁止・空白や引用符禁止・権限 `root:root/644`
  - `systemctl show -p EnvironmentFiles -p Environment noctria_gui` で実際の値を確認

- **GUI から DB 500 / 認証エラー**
  - `NOCTRIA_OBS_PG_DSN` を確認（例: `postgresql://noctria:noctria@127.0.0.1:55432/noctria_db`）
  - `psql` で疎通:  
    `PGPASSWORD=noctria psql -h 127.0.0.1 -p 55432 -U noctria -d noctria_db -c "select 1"`

- **Airflow から `pg-noctria` 解決不可**
  - `docker network connect airflow_docker_default pg-noctria`
  - `docker exec -it noctria_airflow_scheduler getent hosts pg-noctria` で名前解決確認

---

## 9. 開発・運用ルール
1. 新規ファイルはディレクトリ役割を確認し重複機能は統合
2. DAG・戦略は Airflow 上で実行確認を必須
3. GUI テンプレは HUD スタイル（`base_hud.html` 継承）で統一
4. 変更時は `docs/CHANGELOG.md` を更新
5. **環境変数の原則**
   - 開発時: `.env`（uvicorn `--env-file` 可）
   - 常駐時: `/etc/default/noctria-gui`（本書式に従う）

---

## 10. ドキュメント一覧（1〜21 / **リンクはすべて相対パスで docs/ 直下の現構成に整合**）
1. [00-INDEX.md](../00_index/00-INDEX.md) – 本ファイル。全体索引  
2. [Vision-Governance.md](../governance/Vision-Governance.md) – プロジェクト理念・統治モデル  
3. [Architecture-Overview.md](../architecture/Architecture-Overview.md) – アーキテクチャ概要図  
4. [Runbooks.md](../operations/Runbooks.md) – 運用手順書  
5. [Config-Registry.md](../operations/Config-Registry.md) – 設定管理ポリシー  
6. [Airflow-DAGs.md](../operations/Airflow-DAGs.md) – DAG構造・運用ガイド  
7. [ModelCard-Prometheus-PPO.md](../models/ModelCard-Prometheus-PPO.md) – モデル仕様書  
8. [Strategy-Lifecycle.md](../models/Strategy-Lifecycle.md) – 戦略ライフサイクル  
9. [Plan-Layer.md](../architecture/Plan-Layer.md) – Plan層詳細  
10. [API.md](../apis/API.md) – API 仕様書  
11. [Observability.md](../observability/Observability.md) – モニタリングと可観測性  ※APIスコープ版は [`../apis/observability/Observability.md`](../apis/observability/Observability.md)  
12. [Security-And-Access.md](../security/Security-And-Access.md) – セキュリティとアクセス制御  
13. [Testing-And-QA.md](../qa/Testing-And-QA.md) – テスト戦略と品質保証  
14. [Release-Notes.md](../roadmap/Release-Notes.md) – リリースノート  
15. [Roadmap-OKRs.md](../roadmap/Roadmap-OKRs.md) – 中長期計画・OKR  
16. [Coding-Standards.md](../governance/Coding-Standards.md) – コーディング規約  
17. [ADRs.md](../adrs/ADRs.md) – Architecture Decision Records  
18. [Incident-Postmortems.md](../incidents/Incident-Postmortems.md) – インシデント事後分析  
19. [Do-Layer-Contract.md](../apis/Do-Layer-Contract.md) – Do 層 API 契約  
20. [Risk-Register.md](../risks/Risk-Register.md) – リスク登録簿  
21. [howto/](../howto/) – ハウツー集（`howto-*.md`）

---

## 11. 更新履歴
- **2025-08-14**: GUI ルート（`/pdca/timeline`, `/pdca/latency/daily`）追記／Observability 拡充／systemd 常駐（`/etc/default/noctria-gui` + Shell 展開）明文化／Airflow↔DB のネットワーク手順の要点を追記／**ドキュメント一覧（1〜21）を現行ツリーに合わせてリンク修正**  
- **2025-08-12**: ドキュメント一覧を 1〜21 へ拡充  
- **2025-08-12**: 初版作成

<!-- AUTOGEN:CHANGELOG START -->

### 🛠 Updates since: `2025-08-13 17:31 UTC`

- `4715c7b` 2025-08-15T05:12:32+09:00 — **Update update_docs_from_index.py** _(by Noctoria)_
  - `scripts/update_docs_from_index.py`
- `c20a9bd` 2025-08-15T04:58:31+09:00 — **Create update_docs_from_index.py** _(by Noctoria)_
  - `scripts/update_docs_from_index.py`
- `969f987` 2025-08-15T04:36:32+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `a39c7db` 2025-08-15T04:14:15+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `09a3e13` 2025-08-15T03:51:14+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `aea152c` 2025-08-15T03:34:12+09:00 — **Update strategy_detail.py** _(by Noctoria)_
  - `noctria_gui/routes/strategy_detail.py`
- `3bc997c` 2025-08-15T03:23:40+09:00 — **Update strategy_detail.py** _(by Noctoria)_
  - `noctria_gui/routes/strategy_detail.py`
- `482da8a` 2025-08-15T03:02:26+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `feef06f` 2025-08-15T02:33:44+09:00 — **Update docker-compose.yaml** _(by Noctoria)_
  - `airflow_docker/docker-compose.yaml`
- `e4e3005` 2025-08-15T02:15:13+09:00 — **Update __init__.py** _(by Noctoria)_
  - `noctria_gui/__init__.py`
- `4b38d3b` 2025-08-15T01:48:52+09:00 — **Update path_config.py** _(by Noctoria)_
  - `src/core/path_config.py`
- `00fc537` 2025-08-15T01:44:12+09:00 — **Create kpi_minidemo.py** _(by Noctoria)_
  - `src/plan_data/kpi_minidemo.py`
- `daa5865` 2025-08-15T01:37:54+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `5e52eca` 2025-08-15T01:35:28+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `e320246` 2025-08-15T01:34:39+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `de39f94` 2025-08-15T01:33:29+09:00 — **Create Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `e4c82d5` 2025-08-15T01:16:27+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `47a5847` 2025-08-15T01:06:11+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `15188ea` 2025-08-15T00:59:08+09:00 — **Update __init__.py** _(by Noctoria)_
  - `noctria_gui/__init__.py`
- `1b4c2ec` 2025-08-15T00:41:34+09:00 — **Create statistics_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/statistics_routes.py`
- `49795a6` 2025-08-15T00:34:44+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `4d7dd70` 2025-08-15T00:28:18+09:00 — **Update act_service.py** _(by Noctoria)_
  - `src/core/act_service.py`
- `1d38c3c` 2025-08-14T22:21:33+09:00 — **Create policy_engine.py** _(by Noctoria)_
  - `src/core/policy_engine.py`
- `dcdd7f4` 2025-08-14T22:15:59+09:00 — **Update airflow_client.py** _(by Noctoria)_
  - `src/core/airflow_client.py`
- `e66ac97` 2025-08-14T22:08:25+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `6c49b8e` 2025-08-14T21:58:17+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `e0b9eaa` 2025-08-14T21:53:00+09:00 — **Update pdca_summary_service.py** _(by Noctoria)_
  - `src/plan_data/pdca_summary_service.py`
- `368203e` 2025-08-14T21:44:48+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `cc9da23` 2025-08-14T21:32:42+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `434d2e2` 2025-08-14T21:23:55+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `d0df823` 2025-08-14T21:18:54+09:00 — **Update decision_registry.py** _(by Noctoria)_
  - `src/core/decision_registry.py`
- `1eaed26` 2025-08-14T21:08:01+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `b557920` 2025-08-14T21:03:59+09:00 — **Update strategy_evaluator.py** _(by Noctoria)_
  - `src/core/strategy_evaluator.py`
- `0c7a12f` 2025-08-14T21:00:00+09:00 — **Create decision_registry.py** _(by Noctoria)_
  - `src/core/decision_registry.py`
- `2f034a5` 2025-08-14T20:58:16+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `28bb890` 2025-08-14T20:51:37+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `307da2d` 2025-08-14T20:49:15+09:00 — **Create act_service.py** _(by Noctoria)_
  - `src/core/act_service.py`
- `bf993f3` 2025-08-14T20:41:12+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `4b7ca22` 2025-08-14T20:35:18+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `3880c7b` 2025-08-14T20:32:42+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `074b6cf` 2025-08-14T20:24:03+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `46d639d` 2025-08-14T20:17:49+09:00 — **Update strategy_evaluator.py** _(by Noctoria)_
  - `src/core/strategy_evaluator.py`
- `f63e897` 2025-08-14T20:12:50+09:00 — **Update veritas_recheck_dag.py** _(by Noctoria)_
  - `airflow_docker/dags/veritas_recheck_dag.py`
- `7c3785e` 2025-08-14T20:08:26+09:00 — **Create veritas_recheck_all_dag.py** _(by Noctoria)_
  - `airflow_docker/dags/veritas_recheck_all_dag.py`
- `49fe520` 2025-08-14T15:41:00+09:00 — **main.py を更新** _(by Noctoria)_
  - `noctria_gui/main.py`
- `3648612` 2025-08-14T15:35:27+09:00 — **pdca_routes.py を更新** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `f7f1972` 2025-08-14T06:32:19+09:00 — **Update base_hud.html** _(by Noctoria)_
  - `noctria_gui/templates/base_hud.html`
- `eae18c6` 2025-08-14T06:21:35+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `1d6047c` 2025-08-14T06:10:33+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `3c55ed0` 2025-08-14T06:04:20+09:00 — **Create dammy** _(by Noctoria)_
  - `noctria_gui/static/vendor/dammy`
- `7b4624d` 2025-08-14T05:45:03+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `35e4c50` 2025-08-14T04:49:16+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `6c88b9f` 2025-08-14T04:31:58+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `1a0b00e` 2025-08-14T04:29:17+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `2b51ef9` 2025-08-14T04:27:11+09:00 — **Create pdca_summary_service.py** _(by Noctoria)_
  - `src/plan_data/pdca_summary_service.py`
- `6ff093a` 2025-08-14T04:24:34+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `7e2e056` 2025-08-14T04:20:51+09:00 — **Create pdca_control.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_control.html`
- `cf248ee` 2025-08-14T04:15:18+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `d8e0d6e` 2025-08-14T04:12:02+09:00 — **Create airflow_client.py** _(by Noctoria)_
  - `src/core/airflow_client.py`

<!-- AUTOGEN:CHANGELOG END -->
<!-- AUTODOC:BEGIN mode=git_log path_globs=docs/**/*.md title=Docs全体の更新履歴（最近50） limit=50 since=2025-07-01 -->
### Docs全体の更新履歴（最近50）

- **dc39b58** 2025-08-16T04:33:06+09:00 — docs: manual update from index [skip ci] (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/README.md`
  - `docs/_generated/diff_report.md`
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
  - `docs/apis/API.md`
  - `docs/apis/Do-Layer-Contract.md`
  - `docs/architecture/Architecture-Overview.md`
  - `docs/governance/Coding-Standards.md`
- **19cbc79** 2025-08-16T04:15:00+09:00 — Create README_Act_Automation.md (by Noctoria)
  - `docs/operations/PDCA/README_Act_Automation.md`
- **6616bfa** 2025-08-16T03:38:59+09:00 — docs: manual update from index [skip ci] (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/README.md`
  - `docs/_generated/diff_report.md`
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
  - `docs/apis/Do-Layer-Contract.md`
  - `docs/governance/Coding-Standards.md`
  - `docs/governance/Vision-Governance.md`
  - `docs/incidents/Incident-Postmortems.md`
- **558bfd7** 2025-08-16T01:44:43+09:00 — docs: cleanup AUTODOC duplicates and strip stray diff hunks (by Veritas Machina)
  - `.gitignore`
  - `20250603.md.bak`
  - `AirFlow_start.md.bak`
  - `airflow_docker/.env.bak`
  - `airflow_docker/docker/Dockerfile.bak`
  - `airflow_docker/pvc/airflow-dags-pv.yaml.bak`
  - `airflow_docker/pvc/airflow-dags-pvc.yaml.bak`
  - `airflow_docker/scripts/download_veritas_model.py.bak`
  - `airflow_docker/scripts/push_generated_strategy.py.bak`
  - `autogen_scripts/openai_noctria_dev.py.bak`
  - `callmemo_20250602.md.bak`
  - `docs/00_index/00-INDEX.md.bak`
  - `"docs/Next Actions \342\200\224 Noctria PDCA Hardening Plan.md.bak"`
  - `docs/Noctria_Kingdom_System_Design_v2025-08.md.bak`
  - `docs/README.md.bak`
  - `docs/_generated/diff_report.md`
  - `docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md`
  - `docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md`
  - `docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md.bak`
- **c00a20a** 2025-08-16T01:07:45+09:00 — diff check (by Veritas Machina)
  - `docs/_generated/diff_report.md`
- **e79166f** 2025-08-16T00:51:44+09:00 — docs: full-wrap AUTODOC + sync from partials (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/00_index/00-INDEX.md.bak`
  - `"docs/Next Actions \342\200\224 Noctria PDCA Hardening Plan.md"`
  - `"docs/Next Actions \342\200\224 Noctria PDCA Hardening Plan.md.bak"`
  - `docs/Noctria_Kingdom_System_Design_v2025-08.md`
  - `docs/Noctria_Kingdom_System_Design_v2025-08.md.bak`
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
- **d09c7ae** 2025-08-15T05:31:20+09:00 — docs: update from 00-INDEX.md sync (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/_generated/update_docs.log`
  - `docs/adrs/ADRs.md`
  - `docs/apis/API.md`
  - `docs/apis/Do-Layer-Contract.md`
  - `docs/apis/observability/Observability.md`
  - `docs/architecture/Architecture-Overview.md`
  - `docs/architecture/Plan-Layer.md`
  - `docs/governance/Coding-Standards.md`
  - `docs/governance/Vision-Governance.md`
  - `docs/incidents/Incident-Postmortems.md`
  - `docs/models/ModelCard-Prometheus-PPO.md`
  - `docs/models/Strategy-Lifecycle.md`
  - `docs/observability/Observability.md`
  - `docs/operations/Airflow-DAGs.md`
  - `docs/operations/Config-Registry.md`
  - `docs/operations/Runbooks.md`
  - `docs/qa/Testing-And-QA.md`
  - `docs/risks/Risk-Register.md`
  - `docs/roadmap/Release-Notes.md`
- **c29388a** 2025-08-14T03:33:49+09:00 — Update ADRs.md (by Noctoria)
  - `docs/adrs/ADRs.md`
- **d141a4c** 2025-08-14T03:30:22+09:00 — Update Vision-Governance.md (by Noctoria)
  - `docs/governance/Vision-Governance.md`
- **dc7a660** 2025-08-14T03:26:59+09:00 — Update Vision-Governance.md (by Noctoria)
  - `docs/governance/Vision-Governance.md`
- **6112943** 2025-08-14T03:23:05+09:00 — Update howto-*.md (by Noctoria)
  - `docs/howto/howto-*.md`
- **f167207** 2025-08-14T03:16:58+09:00 — Update Testing-And-QA.md (by Noctoria)
  - `docs/qa/Testing-And-QA.md`
- **8021926** 2025-08-14T03:12:38+09:00 — Update Roadmap-OKRs.md (by Noctoria)
  - `docs/roadmap/Roadmap-OKRs.md`
- **05194d5** 2025-08-14T03:09:18+09:00 — Update ModelCard-Prometheus-PPO.md (by Noctoria)
  - `docs/models/ModelCard-Prometheus-PPO.md`
- **1bd84f1** 2025-08-14T03:04:19+09:00 — Update Release-Notes.md (by Noctoria)
  - `docs/roadmap/Release-Notes.md`
- **02b8516** 2025-08-14T02:56:00+09:00 — Update Config-Registry.md (by Noctoria)
  - `docs/operations/Config-Registry.md`
- **1a4b22e** 2025-08-14T02:50:27+09:00 — Update Runbooks.md (by Noctoria)
  - `docs/operations/Runbooks.md`
- **33dd76d** 2025-08-14T02:46:28+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **f1f2743** 2025-08-14T02:42:05+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **32ae51d** 2025-08-14T02:35:42+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **01fec3a** 2025-08-14T02:31:01+09:00 — Update 00-INDEX.md (by Noctoria)
  - `docs/00_index/00-INDEX.md`
- **3f7b49d** 2025-08-14T02:19:26+09:00 — Update 00-INDEX.md (by Noctoria)
  - `docs/00_index/00-INDEX.md`
- **7e68901** 2025-08-13T21:26:36+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **ff8d8c2** 2025-08-13T16:54:25+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **93b1ef1** 2025-08-13T12:09:58+09:00 — Rename Next Actions — Noctria PDCA Hardening Plan to Next Actions — Noctria PDCA Hardening Plan.md (by Noctoria)
  - `"docs/Next Actions \342\200\224 Noctria PDCA Hardening Plan.md"`
- **2e20d48** 2025-08-13T11:55:12+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **cb308f7** 2025-08-13T01:39:56+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **23940b4** 2025-08-13T00:43:38+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **8faf489** 2025-08-13T00:24:16+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **80783ed** 2025-08-13T00:22:34+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **602e45d** 2025-08-12T23:57:03+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **7116954** 2025-08-12T23:44:44+09:00 — Update Observability.md (by Noctoria)
  - `docs/observability/Observability.md`
- **9a3c459** 2025-08-12T23:02:47+09:00 — Update Do-Layer-Contract.md (by Noctoria)
  - `docs/apis/Do-Layer-Contract.md`
- **ce87e75** 2025-08-12T22:54:25+09:00 — Update Testing-And-QA.md (by Noctoria)
  - `docs/qa/Testing-And-QA.md`
- **108b97b** 2025-08-12T22:49:15+09:00 — Update Architecture-Overview.md (by Noctoria)
  - `docs/architecture/Architecture-Overview.md`
- **7da33ee** 2025-08-12T18:22:22+09:00 — Update API.md (by Noctoria)
  - `docs/apis/API.md`
- **c683774** 2025-08-12T18:08:26+09:00 — Update ModelCard-Prometheus-PPO.md (by Noctoria)
  - `docs/models/ModelCard-Prometheus-PPO.md`
- **c428e54** 2025-08-12T18:05:58+09:00 — Update ModelCard-Prometheus-PPO.md (by Noctoria)
  - `docs/models/ModelCard-Prometheus-PPO.md`
- **92cd64e** 2025-08-12T18:01:38+09:00 — Update howto-*.md (by Noctoria)
  - `docs/howto/howto-*.md`
- **14dd164** 2025-08-12T17:57:02+09:00 — Update Incident-Postmortems.md (by Noctoria)
  - `docs/incidents/Incident-Postmortems.md`
- **d62ef46** 2025-08-12T17:18:36+09:00 — Update 00-INDEX.md (by Noctoria)
  - `docs/00_index/00-INDEX.md`
- **9191144** 2025-08-12T17:16:41+09:00 — Update 00-INDEX.md (by Noctoria)
  - `docs/00_index/00-INDEX.md`
- **8bdcdaf** 2025-08-12T17:15:26+09:00 — Rename ADRs to ADRs.md (by Noctoria)
  - `docs/adrs/ADRs.md`
- **f04bab9** 2025-08-12T16:12:50+09:00 — Coding-Standards.md を更新 (by Noctoria)
  - `docs/governance/Coding-Standards.md`
- **c193ed7** 2025-08-12T16:09:23+09:00 — Roadmap-OKRs.md を更新 (by Noctoria)
  - `docs/roadmap/Roadmap-OKRs.md`
- **513e712** 2025-08-12T16:03:18+09:00 — Release-Notes.md を更新 (by Noctoria)
  - `docs/roadmap/Release-Notes.md`
- **887b679** 2025-08-12T13:01:56+09:00 — Testing-And-QA.md を更新 (by Noctoria)
  - `docs/qa/Testing-And-QA.md`
<!-- AUTODOC:END -->
