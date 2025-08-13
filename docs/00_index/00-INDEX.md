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

## 10. ドキュメント一覧（1〜21）
1. `../00_index/00-INDEX.md` – 本ファイル。全体索引  
2. `../governance/Vision-Governance.md` – プロジェクト理念・統治モデル  
3. `../architecture/Architecture-Overview.md` – アーキテクチャ概要図  
4. `../operations/Runbooks.md` – 運用手順書  
5. `../operations/Config-Registry.md` – 設定管理ポリシー  
6. `../operations/Airflow-DAGs.md` – DAG構造・運用ガイド  
7. `../models/ModelCard-Prometheus-PPO.md` – モデル仕様書  
8. `../models/Strategy-Lifecycle.md` – 戦略ライフサイクル  
9. `../architecture/Plan-Layer.md` – Plan層詳細  
10. `../apis/API.md` – API 仕様書  
11. `../observability/Observability.md` – モニタリングと可観測性  
12. `../security/Security-And-Access.md` – セキュリティとアクセス制御  
13. `../qa/Testing-And-QA.md` – テスト戦略と品質保証  
14. `../roadmap/Release-Notes.md` – リリースノート  
15. `../roadmap/Roadmap-OKRs.md` – 中長期計画・OKR  
16. `../governance/Coding-Standards.md` – コーディング規約  
17. `../adrs/ADRs.md` – Architecture Decision Records  
18. `../incidents/Incident-Postmortems.md` – 事後分析  
19. `../apis/Do-Layer-Contract.md` – Do 層 API 契約  
20. `../risks/Risk-Register.md` – リスク登録簿  
21. `../howto/` – ハウツー集

---

## 11. 更新履歴
- **2025-08-14**: GUI ルート（`/pdca/timeline`, `/pdca/latency/daily`）追記／Observability 拡充／systemd 常駐（`/etc/default/noctria-gui` + Shell 展開）明文化／Airflow↔DB のネットワーク手順の要点を追記  
- **2025-08-12**: ドキュメント一覧を 1〜21 へ拡充  
- **2025-08-12**: 初版作成
