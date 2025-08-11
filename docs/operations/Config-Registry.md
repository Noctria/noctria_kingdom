
# 🗄 Config Registry — Noctria Kingdom

**Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：全環境（dev/stg/prod）の**設定を一元管理**し、変更の**安全性・再現性・監査性**を担保する。  
> 参照：`../governance/Vision-Governance.md` / `../operations/Runbooks.md` / `../operations/Airflow-DAGs.md` / `../security/Security-And-Access.md` / `../observability/Observability.md` / `../apis/Do-Layer-Contract.md` / `../schemas/*.schema.json`

---

## 1. 範囲とゴール（Scope）
- 対象：アプリ設定（GUI, Plan/Do/Check/Act）、Airflow、ブローカー/API、リスクポリシー、フラグ類、ログ/監視。  
- ゴール：**環境ごとの差分**を明示し、**誰でも同じ手順で適用**できる状態。  
- 非対象：機密の実値（APIキー/パスワード等）→ Vault/環境変数で管理（§6）。

---

## 2. 原則と優先順位（Precedence）
1. **デフォルト** … `config/defaults.yml`  
2. **環境オーバーライド** … `config/{env}.yml`（`dev|stg|prod`）  
3. **ランタイムフラグ** … `config/flags.yml`（またはGUI/CLI, §6/§7）  
4. **Secrets** … Vault/ENV（ファイルに保存しない）  
> マージは “後勝ち”。キーが被った場合は **Secrets > Flags > {env}.yml > defaults.yml** の順で有効。

---

## 3. ディレクトリ構成（例）
```
config/
  defaults.yml             # 既定値（全環境共通のベース）
  dev.yml                  # 開発環境の上書き
  stg.yml                  # ステージングの上書き
  prod.yml                 # 本番の上書き
  flags.yml                # ランタイムトグル（安全に即時ON/OFF）
  schemas/                 # 内部検証用JSONスキーマ（docs/schemas と同等）
    risk_policy.schema.json
    exec_result.schema.json
```

---

## 4. 環境プロファイル（dev/stg/prod）
- **dev**：自由度重視、モック可、リスク閾値は緩め。  
- **stg**：本番相当で**低ロット**、外部接続はサンドボックス。  
- **prod**：Noctus の**Non-Negotiables**を厳格適用、**監査ログ必須**。  
> タイムゾーンは**JST固定**。AirflowはUTCで運用し、表示でJST補正（`Observability.md` 参照）。

---

## 5. キー命名規則
- 大分類.小分類.項目名（snake_case）  
- 例：`risk_policy.max_drawdown_pct`, `do.broker.kind`, `gui.port`  
- ブールは `is_*/enable_*` を避け、**名詞**で統一（例：`global_trading_pause: true`）。

---

## 6. Secrets（機密情報の扱い）
- 保存場所：**Vault/環境変数のみ**（Gitへコミット禁止）  
- 参照キー例：`VAULT_PATH=noctria/prod/broker`, `ENV BROKER_API_KEY`  
- ローテーション：**90日**またはベンダ規定に従う（`Runbooks.md §10` で手順）  
- 監査：アクセス/読取はSIEMへ転送（`Observability.md`）

---

## 7. ランタイムフラグ（運用トグル）
| キー | 型 | 既定 | 用途 |
|---|---|---|---|
| `flags.global_trading_pause` | bool | false | **全発注停止**（緊急時） |
| `flags.dry_run` | bool | false | 発注をログに限定（検証） |
| `flags.risk_safemode` | bool | true | Noctus 境界を**半分**に厳格化 |
| `flags.enable_notifications` | bool | true | 通知の有効/無効 |

> 切替は `flags.yml` か、運用CLI/GUI（`Runbooks.md §6`）から実施。

---

## 8. リスクポリシー（Noctus 管轄）
- 仕様は `../schemas/risk_policy.schema.json` を正とする。  
- 主要項目：`max_drawdown_pct`, `max_position_qty`, `stop_loss_pct`, `take_profit_pct`, `cooldown_minutes`  
- サンプル：
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

## 9. Airflow 設定（Variables/Connections）
- **Variables（例）**  
  - `env` : `dev|stg|prod`  
  - `risk_policy` : 上記JSON（スキーマに準拠）  
  - `flags` : `flags.yml` をJSON化して反映  
  - `dag_defaults` : `{"retries": 2, "retry_delay": "300s", "sla": "1h"}`  
- **Connections（例）**  
  - `broker_http`（Do層の外部API）  
  - `db_primary`（集計DB）  
- **DAGスケジュール例**  
  - `pdca_check_flow` … `cron: "15 16 * * 1-5"`（EoD後の評価）  
  - `train_prometheus_obs8` … 週次、オフピーク帯

---

## 10. ブローカー/API 設定（Do層）
- 例：
```yaml
do:
  broker:
    kind: "ccxt"         # ccxt|mt5|custom
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
```
> APIキー/シークレットは **Secrets** で注入（§6）。

---

## 11. GUI/サービス設定
```yaml
gui:
  host: "0.0.0.0"
  port: 8000
  base_path: "/"
  auth:
    provider: "basic"   # basic|oidc|none
    require_2fa: true
  features:
    show_pdca_summary: true
    allow_manual_pause: true
```

---

## 12. ログ/監視設定
```yaml
observability:
  log_level: "INFO"            # DEBUG|INFO|WARN|ERROR
  retention_days: 30
  metrics:
    prometheus_port: 9100
  alerts:
    dag_fail_rate_pct: 5
    max_slippage_pct: 0.3
    losing_streak_threshold: 5
```
> 閾値の根拠は `../observability/Observability.md` に記載。

---

## 13. バリデーション（検証とCI）
- **JSON Schema** で検証（`docs/schemas/*.schema.json` を利用）  
- **推奨CI**：PR時に `defaults.yml + {env}.yml + flags.yml + secrets(ダミー)` を合成→JSON化→スキーマ検証  
- 雛形スクリプト（擬似コード）：
```bash
# 例: yq でマージ → jq でJSON化し検証
yq -o=json eval-all '...as $item ireduce ({}; . * $item )' config/defaults.yml config/prod.yml config/flags.yml > /tmp/merged.json
python -m jsonschema -i /tmp/merged.json docs/schemas/risk_policy.schema.json  # 必要なキーごとに検証
```

---

## 14. 変更管理・配布・監査
- **変更はPR**で提出し、`Vision-Governance.md` のRACIに従って承認。  
- **重要変更**はADR作成（`../adrs/`）。  
- **ロールアウト**：`dev → stg（低ロット） → prod（段階導入）`。  
- **監査**：変更差分・適用者・適用時刻を `CHANGELOG` と監査ログに記録（`Runbooks.md §13`）。

---

## 15. 付録：テンプレ／サンプル

### 15.1 `config/defaults.yml`（抜粋）
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
  port: 8000
  base_path: "/"
  auth:
    provider: "basic"
    require_2fa: true

observability:
  log_level: "INFO"
  retention_days: 14
  metrics:
    prometheus_port: 9100
  alerts:
    dag_fail_rate_pct: 5
    max_slippage_pct: 0.3
    losing_streak_threshold: 5
```

### 15.2 `config/prod.yml`（抜粋）
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

### 15.3 `config/flags.yml`（抜粋）
```yaml
flags:
  global_trading_pause: false
  dry_run: false
  risk_safemode: true
  enable_notifications: true
```

### 15.4 `.env.sample`（ENV変数の雛形）
```dotenv
# secrets（※実値はVaultまたはデプロイ環境で設定）
BROKER_API_KEY=
BROKER_API_SECRET=
DB_PRIMARY_URL=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=
```

> 以上を基本テンプレとして、各環境の差分は `{env}.yml` に最小限で記述すること。
