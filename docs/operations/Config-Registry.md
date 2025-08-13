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
