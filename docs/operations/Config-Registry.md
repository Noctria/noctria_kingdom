# 🗄 Config Registry — Noctria Kingdom

**Version:** 1.1  
**Status:** Adopted (pending PR merge)  
**Last Updated:** 2025-08-14 (JST)

> 目的：全環境（dev/stg/prod）の**設定を一元管理**し、変更の**安全性・再現性・監査性**を担保する。  
> 参照：`../governance/Vision-Governance.md` / `../operations/Runbooks.md` / `../operations/Airflow-DAGs.md` / `../security/Security-And-Access.md` / `../observability/Observability.md` / `../apis/Do-Layer-Contract.md`

---

## 1) 範囲とゴール（Scope）
- **対象**：GUI（FastAPI）、Plan/Do/Check/Act、Airflow、ブローカー/API、リスクポリシー、運用フラグ、可観測性。  
- **ゴール**：**環境差分が明示**され、**誰でも同じ手順**で適用・ロールバックできる状態。  
- **非対象**：機密の実値（API キー/パスワード/DSN 等）→ **Vault / 環境変数**で管理（§6）。

---

## 2) 原則と優先順位（Precedence）
1. **defaults** … `config/defaults.yml`（共通ベース）  
2. **env override** … `config/{env}.yml`（`dev|stg|prod`）  
3. **runtime flags** … `config/flags.yml`（運用で即時切替）  
4. **secrets/ENV** … Vault or 環境変数（ファイル化しない）

> マージは **後勝ち**。競合時は `Secrets/ENV > flags.yml > {env}.yml > defaults.yml`。

---

## 3) ディレクトリ構成（標準）
```
config/
  defaults.yml
  dev.yml
  stg.yml
  prod.yml
  flags.yml
  schemas/
    risk_policy.schema.json
    exec_result.schema.json
    decision_profile.schema.json
```

---

## 4) 環境プロファイル（dev/stg/prod）
- **dev**：自由度重視、モック/乾式運転（`flags.dry_run: true` 可）。  
- **stg**：本番同等の設定で **低ロット**、外部はサンドボックス接続。  
- **prod**：Noctus の **Non-Negotiables** を厳格適用、監査ログ強制。

**時刻規約**：内部処理は **UTC**、GUI 表示は **JST**（またはユーザ TZ）。Airflow は UTC 運用。

---

## 5) キー命名規則
- **大分類.小分類.項目名**（snake_case）  
  例：`risk_policy.max_drawdown_pct`, `do.broker.kind`, `gui.port`  
- ブールは `is_*/enable_*` を避け、**名詞**に統一（例：`global_trading_pause: true`）。

---

## 6) Secrets（機密情報）
- **保存場所**：Vault / 環境変数のみ（Git へコミット禁止）  
- **例（環境変数）**  
  - `NOCTRIA_OBS_PG_DSN`（観測系 DB DSN）  
  - `BROKER_API_KEY` / `BROKER_API_SECRET`  
- **ローテーション**：90 日またはベンダ規定  
- **監査**：読取/使用は SIEM（可観測性）へ転送

> **GUI（systemd）では以下の ENV を /etc/default で注入**：  
> `NOCTRIA_OBS_PG_DSN`, `NOCTRIA_GUI_PORT`（詳細は §11 と付録 A）

---

## 7) ランタイムフラグ（運用トグル）
| キー | 型 | 既定 | 用途 |
|---|---|---|---|
| `flags.global_trading_pause` | bool | false | **全発注停止**（緊急停止スイッチ） |
| `flags.dry_run` | bool | false | **発注をログに限定**（検証時） |
| `flags.risk_safemode` | bool | true | Noctus 境界を **厳格化**（安全側） |
| `flags.enable_notifications` | bool | true | GUI 内通知の表示可否 |

> 切替は `flags.yml` または運用 CLI/GUI（Runbooks §7）。

---

## 8) リスクポリシー（Noctus 管轄）
- 仕様は `docs/schemas/risk_policy.schema.json` を **SoT**（Source of Truth）。  
- 主要項目：`max_drawdown_pct`, `max_position_qty`, `stop_loss_pct`, `take_profit_pct`, `cooldown_minutes`。  
- **サンプル**：
```json
{
  "max_drawdown_pct": 10.0,
  "max_position_qty": 100000,
  "stop_loss_pct": 1.5,
  "take_profit_pct": 3.0,
  "cooldown_minutes": 15
}
```

---

## 9) Airflow（Variables / Connections / Schedules）
- **Variables（例）**  
  - `env`: `dev|stg|prod`  
  - `risk_policy`: §8 JSON  
  - `flags`: `flags.yml` を JSON 化して反映  
  - `dag_defaults`: `{"retries": 2, "retry_delay": "300s", "sla": "1h"}`  
- **Connections（例）**  
  - `db_primary`（観測/集計 DB）  
  - `broker_http`（Do 層外部 API）  
- **スケジュール例**  
  - `pdca_check_flow` … EoD 後（例：`15 16 * * 1-5`）  
  - `train_prometheus_obs8` … 週次オフピーク

---

## 10) Do 層（ブローカー/API・注文実行）
```yaml
do:
  broker:
    kind: "ccxt"            # ccxt|mt5|custom
    base_url: "https://api.broker.example"
    timeout_sec: 10
    rate_limit_qps: 8
    symbol_map:
      BTCUSDT: "BTC/USDT"
      ETHUSDT: "ETH/USDT"
  order:
    max_slippage_pct: 0.2
    time_in_force: "GTC"
    partial_fill_allowed: true
  idempotency:
    outbox_enabled: false    # 将来の厳格化に備えたフラグ
```
> API キー/シークレットは **ENV/Vault** で注入（§6）。

---

## 11) GUI / サービス設定（systemd 運用）
```yaml
gui:
  host: "0.0.0.0"
  port: 8001                 # 既定ポートは 8001（ENV: NOCTRIA_GUI_PORT で上書き）
  base_path: "/"
  auth:
    provider: "basic"        # basic|oidc|none（RBAC は将来導入）
    require_2fa: true
  features:
    show_pdca_summary: true
    allow_manual_pause: true

ops:
  systemd:
    unit_name: "noctria_gui.service"
    environment_file: "/etc/default/noctria-gui"
    # ExecStart は ENV 展開のため /bin/sh 経由で実行する（Runbooks §4 参照）
```

**重要**（本リリースの変更点）
- 既定ポートを **8000 → 8001** に変更。  
- **/etc/default/noctria-gui** で `NOCTRIA_GUI_PORT` を注入し、`ExecStart` は **`/bin/sh -lc 'exec ... --bind 0.0.0.0:${NOCTRIA_GUI_PORT:-8001}'`** で起動（ENV 展開のため）。

---

## 12) 可観測性（Observability）
```yaml
observability:
  log_level: "INFO"          # DEBUG|INFO|WARN|ERROR
  retention_days: 30         # 原始イベント保持（ロールアップは日次）
  alerts:
    dag_fail_rate_pct: 5
    max_slippage_pct: 0.3
    losing_streak_threshold: 5
  compat:
    legacy_exec_tables: false # true の場合、obs_orders/obs_trades も出力
```
- **テーブル/ビュー（要約）**：`obs_api_requests`, `obs_infer_calls`, `obs_plan_runs`, `obs_decisions`, `obs_exec_events`, `obs_alerts`, `obs_latency_daily`（詳細は Observability.md）。  
- **GUI**：`/pdca/timeline`, `/pdca/latency/daily`, `POST /pdca/observability/refresh`。

---

## 13) Decision Engine（外部プロファイル）
```yaml
decision:
  profiles_file: "configs/profiles.yaml"  # 重み/しきい値/ロールアウト率を外部化
  api_version: "v1"                       # 互換ポリシー（SemVer）
```
- **契約**：`/api/v1`、変更系は **Idempotency-Key 必須**、互換破壊は `v2` で実施。

---

## 14) バリデーション（CI 推奨）
- PR 時に `defaults.yml + {env}.yml + flags.yml + (dummy secrets)` をマージ→JSON 化→**JSON Schema** で検証。  
- 雛形（例）：
```bash
# yq で YAML マージ → jq で JSON 化 → jsonschema で検証
yq -o=json eval-all '... as $item ireduce ({}; . * $item )' \
  config/defaults.yml config/prod.yml config/flags.yml > /tmp/merged.json

python -m jsonschema -i /tmp/merged.json docs/schemas/risk_policy.schema.json
# 必要に応じて decision_profile.schema.json / exec_result.schema.json も検証
```

---

## 15) 変更管理・配布・監査
- **変更は PR** で提出し、`Vision-Governance.md` の RACI に従って承認。  
- **重要変更** は ADR を作成（`../adrs/`）。  
- **ロールアウト**：`dev → stg（低ロット） → prod（段階導入 7→30→100%）`。  
- **監査**：差分・適用者・適用時刻を `CHANGELOG` と監査ログに記録（Runbooks §14）。

---

## 16) 互換/移行（Breaking Changes）
- **v1.1**：GUI 既定ポートを **8001** に変更し、**systemd + /etc/default** で ENV を注入。  
  - 影響：FW/ALB/Compose のポートを確認・更新。  
  - `/etc/default/noctria-gui` は **LF/644/root:root**。CRLF 混入に注意。  
  - `ExecStart` は **/bin/sh -lc** 経由で ENV を展開（Runbooks §10.1 参照）。

---

## 17) 付録（テンプレ & サンプル）

### 17-A) `/etc/default/noctria-gui`（ENV）
```dotenv
NOCTRIA_OBS_PG_DSN=postgresql://noctria:noctria@127.0.0.1:55432/noctria_db
NOCTRIA_GUI_PORT=8001
```

### 17-B) systemd ユニット（抜粋・推奨形）
```ini
[Service]
EnvironmentFile=/etc/default/noctria-gui
Environment=PYTHONUNBUFFERED=1
WorkingDirectory=/mnt/d/noctria_kingdom
ExecStart=/bin/sh -lc 'exec /mnt/d/noctria_kingdom/venv_gui/bin/gunicorn \
  --workers 4 --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${NOCTRIA_GUI_PORT:-8001} \
  --access-logfile - --error-logfile - \
  noctria_gui.main:app'
Restart=always
```

### 17-C) `config/defaults.yml`（抜粋）
```yaml
env: "dev"

flags:
  global_trading_pause: false
  dry_run: false
  risk_safemode: true
  enable_notifications: true

risk_policy:
  max_drawdown_pct: 12.0
  max_position_qty: 50000
  stop_loss_pct: 2.0
  take_profit_pct: 4.0
  cooldown_minutes: 10

do:
  broker:
    kind: "ccxt"
    base_url: "https://sandbox.example"
    timeout_sec: 10
    rate_limit_qps: 8
  order:
    max_slippage_pct: 0.25
    time_in_force: "GTC"
    partial_fill_allowed: true

gui:
  host: "0.0.0.0"
  port: 8001
  base_path: "/"
  auth:
    provider: "basic"
    require_2fa: true
  features:
    show_pdca_summary: true
    allow_manual_pause: true

observability:
  log_level: "INFO"
  retention_days: 30
  alerts:
    dag_fail_rate_pct: 5
    max_slippage_pct: 0.3
    losing_streak_threshold: 5
  compat:
    legacy_exec_tables: false

decision:
  profiles_file: "configs/profiles.yaml"
  api_version: "v1"
```

### 17-D) `config/prod.yml`（抜粋）
```yaml
env: "prod"

risk_policy:
  max_drawdown_pct: 8.0
  stop_loss_pct: 1.0
  take_profit_pct: 2.5
  cooldown_minutes: 30

do:
  broker:
    base_url: "https://api.broker.example"

observability:
  log_level: "WARN"
  retention_days: 30
```

### 17-E) `config/flags.yml`（抜粋）
```yaml
flags:
  global_trading_pause: false
  dry_run: false
  risk_safemode: true
  enable_notifications: true
```

### 17-F) `.env.sample`（参考：実値は Vault/ENV で注入）
```dotenv
# Database / Observability
NOCTRIA_OBS_PG_DSN=

# Broker
BROKER_API_KEY=
BROKER_API_SECRET=

# OIDC（使用時）
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=
```

---

## 18) 変更履歴
- **2025-08-14**: **v1.1**
  - GUI 既定ポートを **8001** に更新、systemd + `/etc/default/noctria-gui` の運用方針を正式化
  - Observability に `obs_decisions` / `obs_exec_events` を追記、レガシー互換フラグを追加
  - DecisionEngine の外部プロファイル（`configs/profiles.yaml`）を正式化
- **2025-08-12**: v1.0 初版

<!-- AUTOGEN:CHANGELOG START -->

### 🛠 Updates since: `2025-08-13 17:56 UTC`

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
<!-- AUTODOC:BEGIN mode=git_log path_globs="src/core/settings.py;src/core/config/**/*.py;docs/operations/*.md" title=設定/レジストリ更新履歴（最近30） limit=30 since=2025-08-01 -->
### 設定/レジストリ更新履歴（最近30）

- **2ec153a** 2025-08-19T03:43:50+09:00 — docs: manual update from index [skip ci] (by Veritas Machina)
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
  - `docs/architecture/Plan-Layer.md`
- **702afb6** 2025-08-17T21:44:33+09:00 — docs: manual update from index [skip ci] (by Veritas Machina)
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
- **02b8516** 2025-08-14T02:56:00+09:00 — Update Config-Registry.md (by Noctoria)
  - `docs/operations/Config-Registry.md`
- **1a4b22e** 2025-08-14T02:50:27+09:00 — Update Runbooks.md (by Noctoria)
  - `docs/operations/Runbooks.md`
- **3373062** 2025-08-12T10:56:04+09:00 — Airflow-DAGs.md を更新 (by Noctoria)
  - `docs/operations/Airflow-DAGs.md`
- **3998941** 2025-08-12T04:39:48+09:00 — Update Config-Registry.md (by Noctoria)
  - `docs/operations/Config-Registry.md`
- **05d3f5d** 2025-08-12T04:36:19+09:00 — Update Runbooks.md (by Noctoria)
  - `docs/operations/Runbooks.md`
- **a410532** 2025-08-12T03:01:21+09:00 — Create Airflow-DAGs.md (by Noctoria)
  - `docs/operations/Airflow-DAGs.md`
- **9371b3c** 2025-08-12T03:01:04+09:00 — Create Config-Registry.md (by Noctoria)
  - `docs/operations/Config-Registry.md`
- **ee7cb52** 2025-08-12T03:00:26+09:00 — Create Runbooks.md (by Noctoria)
  - `docs/operations/Runbooks.md`
<!-- AUTODOC:END -->
