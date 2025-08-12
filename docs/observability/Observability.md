# 🔭 Observability — Noctria Kingdom

**Version:** 1.0  
**Status:** Adopted  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の PDCA（Plan/Do/Check/Act）と統治基盤（GUI/Airflow/API）の**状態を可視化**し、**逸脱を即検知**・**根因追跡**・**説明可能性**を担保する。  
> 参照：`../architecture/Architecture-Overview.md` / `../apis/API.md` / `../apis/Do-Layer-Contract.md` / `../qa/Testing-And-QA.md` / `../operations/Runbooks.md` / `../security/Security-And-Access.md`

---

## 1. スタック & 原則
- **スタック**：Prometheus（メトリクス）/ Loki（構造化ログ）/ Grafana（可視化）/ OTel → Tempo or Jaeger（トレース）。  
- **原則**：
  1) **Guardrails First**：Noctus 境界と KPI の逸脱を**最優先**で検知。  
  2) **Correlation**：`X-Correlation-ID` を**メトリクス・ログ・トレース**に横断付与。  
  3) **SLO/SLA as Code**：Prometheus ルール・SLO を Git 管理（PR で改訂）。  
  4) **低ノイズ**：Alert は**少数・高精度**（Multi-window burn rate + 抑制条件）。  
  5) **WORM**：`audit_order.json` は監査専用ストア（改変不可）。

**ディレクトリ**
```
deploy/observability/
  prometheus/
    rules/          # recording/alerting rules (YAML)
  loki/
    pipeline/       # labels, parsers
dashboards/
  grafana/*.json    # provisioned dashboards
```

---

## 2. 計測ドメイン & メトリクス規約
- **命名**：`<layer>_<subject>_<metric>_{seconds|total|pct|gauge}`  
  - 例：`do_order_latency_seconds`（Histogram）、`plan_features_recency_seconds`（Gauge）  
- **ラベル**（最小）：`env`, `layer`, `component`, `symbol`, `strategy`, `status`, `broker`, `dag_id`, `task_id`, `tf`  
- **ヒストグラム既定バケット**
  - レイテンシ（秒）：`[0.05,0.1,0.2,0.3,0.5,0.75,1,1.5,2,3,5]`
  - スリッページ（%）：`[0.05,0.1,0.2,0.3,0.5,0.75,1,1.5,2]`

**主要メトリクス（抜粋）**
| 名称 | 種別 | 説明 |
|---|---|---|
| `do_order_requests_total{status}` | Counter | 成功/失敗/拒否 |
| `do_order_latency_seconds` | Hist | Do 層 API〜結果まで |
| `do_slippage_pct` | Hist | 滑り率（約定ごと） |
| `risk_events_total{kind,severity}` | Counter | Noctus 発火件数 |
| `plan_features_recency_seconds` | Gauge | 最新特徴量の遅延 |
| `airflow_dag_sla_miss_total{dag_id}` | Counter | SLA 違反 |
| `kpi_win_rate` / `kpi_max_dd_pct` / `kpi_sharpe_adj` | Gauge | Check 層 KPI スナップ |
| `api_http_requests_total{route,status}` | Counter | API 呼出し数 |
| `api_http_request_duration_seconds` | Hist | API レイテンシ |

---

## 3. SLO/SLA（数値確定）
**対象：prod（stg は +20% 緩和）**

| SLO 名 | 目標 | 説明 |
|---|---|---|
| Do レイテンシ p95 | ≤ **0.50s** | `do_order_latency_seconds{env="prod"}` |
| Do エラー率 | ≤ **0.5%** | `rate(do_order_requests_total{status=~"5..|REJECTED"}[5m]) / rate(do_order_requests_total[5m])` |
| スリッページ p90 | ≤ **0.30%** | `histogram_quantile(0.90, sum by (le) (rate(do_slippage_pct_bucket[10m])))` |
| 特徴量遅延 | ≤ **120s** | `plan_features_recency_seconds` |
| DAG SLA 違反率 | ≤ **0.5%/day** | `increase(airflow_dag_sla_miss_total[1d]) / total_dag_runs` |
| KPI 安定 | `win_rate≥0.50` & `max_dd≤8%` | 7d 移動窓 |

**SLI 記録ルール（例）**
```yaml
# deploy/observability/prometheus/rules/sli.yaml
groups:
- name: noctria_sli
  rules:
  - record: do:latency:p95
    expr: |
      histogram_quantile(0.95, sum by (le) (rate(do_order_latency_seconds_bucket{env="prod"}[5m])))
  - record: do:error_rate
    expr: |
      sum(rate(do_order_requests_total{env="prod",status=~"5..|REJECTED"}[5m]))
      /
      sum(rate(do_order_requests_total{env="prod"}[5m]))
  - record: do:slippage:p90
    expr: |
      histogram_quantile(0.90, sum by (le) (rate(do_slippage_pct_bucket{env="prod"}[10m])))
```

---

## 4. アラート（PromQL, Loki）— Multi-window/Burn-rate
**Severity 基準**：`CRITICAL`=即時人間対応 / `HIGH`=当日中 / `MEDIUM`=業務時間 / `LOW`=週次レビュー

```yaml
# deploy/observability/prometheus/rules/alerts.yaml
groups:
- name: do_layer_alerts
  rules:
  # A) エラー率 SLO 逸脱（多窓バーン：2h と 15m）
  - alert: DoErrorBudgetBurn
    expr: |
      (sum(rate(do_order_requests_total{env="prod",status=~"5..|REJECTED"}[2h])) 
       / sum(rate(do_order_requests_total{env="prod"}[2h])) > 0.01)
      and
      (sum(rate(do_order_requests_total{env="prod",status=~"5..|REJECTED"}[15m])) 
       / sum(rate(do_order_requests_total{env="prod"}[15m])) > 0.02)
    for: 5m
    labels: {severity: "CRITICAL", team: "do"}
    annotations:
      summary: "Do error-rate burn (2h/15m)"
      runbook_url: "/docs/operations/Runbooks.md#8-ロールバック"

  # B) レイテンシ p95 劣化
  - alert: DoLatencyP95High
    expr: do:latency:p95{env="prod"} > 0.5
    for: 10m
    labels: {severity: "HIGH", team: "do"}
    annotations:
      summary: "Do p95 latency > 0.5s (10m)"
      runbook_url: "/docs/operations/Runbooks.md#7-遅延スパイク対応"

  # C) スリッページスパイク
  - alert: SlippageSpike
    expr: do:slippage:p90{env="prod"} > 0.3
    for: 10m
    labels: {severity: "HIGH", team: "risk"}
    annotations:
      summary: "p90 slippage > 0.30% (10m)"
      runbook_url: "/docs/operations/Runbooks.md#6-スリッページ急騰"

- name: plan_check_alerts
  rules:
  # D) 特徴量遅延
  - alert: PlanFeaturesStale
    expr: plan_features_recency_seconds{env="prod"} > 120
    for: 5m
    labels: {severity: "MEDIUM", team: "plan"}
    annotations:
      summary: "Features recency > 120s"
      runbook_url: "/docs/architecture/Plan-Layer.md#データ新鮮度"

  # E) KPI 劣化（7d）
  - alert: KpiDegradation
    expr: (kpi_win_rate{env="prod"} < 0.50) or (kpi_max_dd_pct{env="prod"} > 8)
    for: 12h
    labels: {severity: "MEDIUM", team: "models"}
    annotations:
      summary: "KPI degradation 7d (win_rate or max_dd)"
      runbook_url: "/docs/models/Strategy-Lifecycle.md#降格条件"
```

**Loki（構造化ログ）例**
```logql
# エラー多発の相関（Do 層）
{component="do.order_execution", env="prod", level="ERROR"}
| json
| count_over_time({component="do.order_execution"}[15m])
```

---

## 5. ログ（構造化 JSON）& トレース（OTel）
**JSON ログ共通フィールド**
```json
{
  "ts":"2025-08-12T06:58:03Z",
  "level":"INFO",
  "component":"do.order_execution",
  "msg":"order filled",
  "env":"prod",
  "correlation_id":"6f1d3b34-...",
  "order_id":"SIM-12345",
  "symbol":"BTCUSDT",
  "strategy":"Prometheus-PPO",
  "duration_ms":190
}
```
- **禁止**：Secrets/PII。詳細は `../security/Security-And-Access.md`。  
- **Loki ラベル**：`{env,component,level,strategy,symbol}`（カードinality を制御）。  

**OTel（トレース）**
- **必須属性**：`service.name`, `noctria.env`, `order.id`, `correlation.id`, `strategy`, `symbol`, `risk.boundary_hit`。  
- **サンプリング**：標準 10%、`ERROR`/`risk_event` 伴う span は**必ず 100%**。

---

## 6. ダッシュボード（Grafana）
- **Do Layer Overview**：レイテンシヒスト/エラー率/スリッページ p90・p99 / ブローカー別。  
- **Plan/Features Freshness**：`plan_features_recency_seconds`（シンボル×TF）、欠損・重複。  
- **KPI & Adoption**：`kpi_*` と段階導入（7%→30%→100%）の**注釈**。  
- **Airflow Health**：DAG 実行数/SLA 違反/キュー滞留。  
- **Audit Explorer**：`audit_order.json` の件数/遅延/境界ヒット率。  

**注釈（自動）**
- リリース/段階導入/抑制ON/OFF/リスク境界改訂は**必ず注釈**（`howto-start-canary.md` / `howto-trading-pause.md`）。

---

## 7. 合成監視（Synthetics）
- `/api/v1/healthz`：60 秒間隔。SLO：連続失敗 3 回で `CRITICAL`。  
- `/api/v1/version`：Git SHA 差替時に**注釈**。  
- `/api/v1/alerts/stream`（SSE）：再接続（`Last-Event-ID`）動作を**外形監視**。  

---

## 8. コスト & 保持
- **Prometheus**：原則 30 日（Recording で集約）。  
- **Loki**：アプリログ 30 日、`audit_order` 参照ログは 90 日（監査 WORM は長期別保管）。  
- **Traces**：7〜14 日（`ERROR`/`risk_event` 関連は 30 日）。  
- ラベル爆増の抑制：`strategy` は主要のみに限定、テナント/テストは `env` で分離。

---

## 9. 運用（アラートルーティング）
| 種別 | 送信先 | 付記 |
|---|---|---|
| CRITICAL | PagerDuty/電話 | 24/7 候補者 2 名（エスカレーション） |
| HIGH | Slack `#ops-alerts` + メール | 10 分ごとに再通知 |
| MEDIUM | Slack `#ops` | 営業時間内で対応 |
| LOW | 週次レポート | 週次レビュー |

**メンテナンス/抑制**
- デプロイ直後 10 分、カナリア移行 10 分は**アラート抑制**（メタラベル `annotation=deploy|canary`）。

---

## 10. Runbooks 連携（一次対応）
- `DoErrorBudgetBurn` → `Runbooks.md §8 （ロールバック/停止→復帰）`  
- `DoLatencyP95High` → `Runbooks.md §7 （遅延スパイク）`  
- `SlippageSpike` → `Runbooks.md §6 （スリッページ）`  
- `PlanFeaturesStale` → `Plan-Layer.md §6 （再収集/バックフィル）`  
- `KpiDegradation` → `Strategy-Lifecycle.md §4.5 （降格/再評価）`

---

## 11. 実装ガイド（インスツルメンテーション）
**Python（OTel + Prometheus クライアント）**
```python
from prometheus_client import Histogram, Counter
order_latency = Histogram("do_order_latency_seconds", "Do end-to-end latency",
                          buckets=[0.05,0.1,0.2,0.3,0.5,0.75,1,1.5,2,3,5])
orders_total = Counter("do_order_requests_total", "Do orders", ["status"])

# usage
with order_latency.time():
    status = process_order(req)
orders_total.labels(status=status).inc()
```

**FastAPI（Correlation ID 中継）**
```python
async def correlation_mw(request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response
```

---

## 12. 品質基準（DoD）
- SLO 定義済 & ダッシュボード/ルールが**Git に存在**。  
- 主要メトリクス & ログ & トレースが**相互に辿れる**（Correlation ID）。  
- Alert は Runbooks へリンク済、**誤検知率 < 2%** を目標。  
- 変更は **同一PR** で `Testing-And-QA.md` とゲート条件を更新。

---

## 13. 変更履歴（Changelog）
- **2025-08-12**: 初版作成（SLO 数値確定／記録ルール／Multi-window アラート／ログ・トレース規約／ダッシュボード＆Runbooks 連携）
