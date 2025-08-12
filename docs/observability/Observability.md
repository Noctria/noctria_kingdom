# 🔭 Observability — Noctria Kingdom（HUD版 / Grafanaなし）

**Version:** 1.1  
**Status:** Adopted  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の PDCA（Plan/Do/Check/Act）と統治基盤（GUI/Airflow/API）の**状態を可視化**し、**逸脱を即検知**・**根因追跡**・**説明可能性**を担保する。  
> 前提：**FastAPI + Gunicorn（Uvicorn workers）** を標準。Prometheus は**任意**（/metrics が出せるなら利用、無ければ /metrics.json で代替）。  
> 参照：`../apis/API.md` / `../apis/Do-Layer-Contract.md` / `../qa/Testing-And-QA.md` / `../operations/Runbooks.md` / `../security/Security-And-Access.md`

---

## 1. スタック & 原則（Grafanaなし構成）
- **可視化**：FastAPI GUI 内の **HUD**（`/hud/observability`）。ECharts/Chart.js 等で描画。
- **収集**：
  - A) **Prometheusあり**：`prometheus_client` で `/metrics` を公開（推奨）。  
  - B) **Prometheusなし**：アプリ内でカウンタ/ヒストグラムを集計し、`/metrics.json` を返す。
- **アラート**：FastAPI 内の **スケジューラ（APScheduler or 自作）** が SLI/SLO を定期判定し、**Slack Webhook** へ通知。
- **ログ**：Gunicorn/Uvicorn の**構造化JSON**を標準出力。`correlation_id`, `env`, `component`, `latency_ms` は必須。
- **原則**：
  1) **Guardrails First**：Noctus 境界と KPI の逸脱を最優先で検知。  
  2) **Correlation**：`X-Correlation-ID` を**メトリクス・ログ**に横断付与。  
  3) **SLO as Code**：しきい値/判定式をコードと本書で**単一情報源**化。  
  4) **低ノイズ**：アラートは**多窓（長窓×短窓）**で誤検知を抑制。  

**ディレクトリ（推奨）**
```
app/
  observability/                     # 本章の実装一式
    hud.py                           # /hud/observability ルート
    metrics.py                       # /metrics or /metrics.json とカウンタ類
    alerts.py                        # APScheduler ベースの SLx 判定 + Slack 通知
deploy/
  logging/uvicorn_gunicorn.conf      # Gunicorn 起動オプション（JSON ログ）
```

---

## 2. メトリクス規約（名前・ラベル・バケット）
- **命名**：`<layer>_<subject>_<metric>_{seconds|total|pct|gauge}`  
  - 例：`do_order_latency_seconds`（ヒスト） / `do_slippage_pct`（ヒスト） / `plan_features_recency_seconds`（ゲージ）
- **最低ラベル**：`env`, `layer`, `component`, `symbol`, `strategy`, `status`, `broker`, `tf`
- **ヒストグラム既定バケット**  
  - レイテンシ（秒）：`[0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 5]`  
  - スリッページ（%）：`[0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2]`

**主要メトリクス（抜粋）**
| 名称 | 種別 | 説明 |
|---|---|---|
| `do_order_requests_total{status}` | Counter | 成功/失敗/拒否件数 |
| `do_order_latency_seconds` | Histogram | Do 層 E2E レイテンシ |
| `do_slippage_pct` | Histogram | 取引ごとの滑り率（%） |
| `risk_events_total{kind,severity}` | Counter | Noctus の境界発火件数 |
| `plan_features_recency_seconds` | Gauge | 最新特徴量の遅延（秒） |
| `kpi_win_rate` / `kpi_max_dd_pct` | Gauge | Check 層 KPI スナップ |

---

## 3. SLO/SLA（数値確定：prod／stg は +20% 緩和）
| SLO 名 | 目標 | 説明 |
|---|---|---|
| Do レイテンシ p95 | ≤ **0.50s** | `do_order_latency_seconds` |
| Do エラー率 | ≤ **0.5%** | `5xx + REJECTED` / 全リクエスト（5分窓） |
| スリッページ p90 | ≤ **0.30%** | 10分窓 |
| 特徴量遅延 | ≤ **120s** | `plan_features_recency_seconds` |
| KPI 安定 | `win_rate ≥ 0.50` & `max_dd ≤ 8%` | 7日窓 |

**SLI 算出（Prometheus ありの場合の式イメージ）**  
- p95 レイテンシ：`histogram_quantile(0.95, sum by (le) (rate(do_order_latency_seconds_bucket[5m])))`  
- エラー率：`sum(rate(do_order_requests_total{status=~"5..|REJECTED"}[5m])) / sum(rate(do_order_requests_total[5m]))`  
- p90 スリッページ：`histogram_quantile(0.90, sum by (le) (rate(do_slippage_pct_bucket[10m])))`

**Prometheus がない場合**：アプリ内で p 分位（p95/p90）と比率を計算し、`/metrics.json` に載せる。

---

## 4. アラート（HUD版：アプリ内スケジューラ）
**判定ルール（長窓 × 短窓 の多窓バーン）**
- **DoErrorBudgetBurn**：2h 窓 > 1% **かつ** 15m 窓 > 2%（5分連続）→ **CRITICAL**  
- **DoLatencyP95High**：p95 > 0.5s（10分連続）→ **HIGH**  
- **SlippageSpike**：p90 > 0.30%（10分連続）→ **HIGH**  
- **PlanFeaturesStale**：`recency > 120s`（5分連続）→ **MEDIUM**  
- **KpiDegradation**：`win_rate < 0.50` **or** `max_dd > 8`（12h）→ **MEDIUM**

**通知**：Slack `#ops-alerts`（Webhook）。Runbooks の該当章リンクを必ず添付。  
**抑制**：デプロイ直後 / 段階導入切替の 10 分は抑制（HUD トーストで注釈表示）。

---

## 5. 実装（抜粋スニペット）
### 5.1 メトリクス（/metrics or /metrics.json）
```python
# app/observability/metrics.py
from fastapi import APIRouter
from datetime import datetime, timezone
from collections import deque
from typing import Optional

router = APIRouter()
BUCKETS_LAT = [0.05,0.1,0.2,0.3,0.5,0.75,1,1.5,2,3,5]

# 環境に Prometheus がある場合は自動利用（無ければ JSON 返却）
try:
    from prometheus_client import Histogram, Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROM = True
    do_latency = Histogram("do_order_latency_seconds", "Do latency (E2E)", buckets=BUCKETS_LAT)
    do_total = Counter("do_order_requests_total", "Do requests", ["status"])
    do_slip = Histogram("do_slippage_pct", "Slippage pct", buckets=[0.05,0.1,0.2,0.3,0.5,0.75,1,1.5,2])
    features_recency = Gauge("plan_features_recency_seconds", "Features recency (s)")
    kpi_win_rate = Gauge("kpi_win_rate", "Win rate (0..1)")
    kpi_max_dd = Gauge("kpi_max_dd_pct", "Max drawdown (%)")
except Exception:
    PROM = False

# Prometheus が無い場合の軽量集計（直近10分）
WINDOW = deque(maxlen=600)  # 1秒サンプル * 600 = 10分
STATE = {"errors":0, "total":0, "features_recency":0.0, "kpi":{"win_rate":None,"max_dd_pct":None}}

def pct(xs, q):
    if not xs: return None
    s = sorted(xs); i = max(0, min(len(s)-1, int(q*(len(s)-1))))
    return s[i]

@router.get("/metrics")
def metrics():
    if PROM:
        from fastapi.responses import Response
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    # Prometheus 無し：JSON を返す
    now = datetime.now(timezone.utc).isoformat()
    lat = [x["lat"] for x in WINDOW if "lat" in x]
    slip = [x["slip"] for x in WINDOW if "slip" in x]
    err_rate = (STATE["errors"]/STATE["total"]) if STATE["total"] else 0.0
    return {
        "ts": now,
        "latency_p95": pct(lat, 0.95),
        "error_rate": err_rate,
        "slippage_p90": pct(slip, 0.90),
        "features_recency_s": STATE["features_recency"],
        "kpi": STATE["kpi"]
    }

#（アプリの処理側で do_latency.time() や WINDOW.append(...) を呼び出して集計する）
```

### 5.2 HUD ルート（/hud/observability）
```python
# app/observability/hud.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
router = APIRouter()

@router.get("/hud/observability", response_class=HTMLResponse)
def hud():
    # 最小のカード表示（CSS/JS はプロジェクト共通の HUD を想定）
    return """
    <section class="grid grid-cols-2 gap-4">
      <div class="card"><h3>Do p95 latency</h3><div id="lat_p95">--</div><small>SLO ≤ 0.50s</small></div>
      <div class="card"><h3>Do error-rate</h3><div id="err">--</div><small>SLO ≤ 0.5%</small></div>
      <div class="card"><h3>p90 slippage</h3><div id="slip">--</div><small>SLO ≤ 0.30%</small></div>
      <div class="card"><h3>Features recency</h3><div id="rec">--</div><small>≤ 120s</small></div>
    </section>
    <script>
    async function refresh(){
      const res = await fetch('/metrics'); const m = await res.json();
      const p95 = (m.latency_p95 ?? 0).toFixed(3)+'s';
      const er  = ((m.error_rate ?? 0)*100).toFixed(2)+'%';
      const p90 = (m.slippage_p90 ?? 0).toFixed(2)+'%';
      const fr  = (m.features_recency_s ?? 0).toFixed(0)+'s';
      document.getElementById('lat_p95').innerText = p95;
      document.getElementById('err').innerText = er;
      document.getElementById('slip').innerText = p90;
      document.getElementById('rec').innerText = fr;
    }
    setInterval(refresh, 5000); refresh();
    </script>
    """
```

### 5.3 アラート（APScheduler + Slack）
```python
# app/observability/alerts.py
import os, json, httpx, asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

def within(v, hi): return v is not None and v > hi
def below(v, lo): return v is not None and v < lo

async def notify(kind, text, runbook="#"):
    if not SLACK_WEBHOOK: return
    payload = {"text": f"[{kind}] {text}\nRunbook: {runbook}"}
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(SLACK_WEBHOOK, json=payload)

async def poll_metrics():
    # Prometheus 無し前提の /metrics.json 取得（/metrics でもOK）
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8000/metrics")
            m = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
    except Exception:
        return
    # 多窓バーン：ここでは簡略化（短窓のみ）。実運用はリングバッファで短窓/長窓を併記。
    if within(m.get("latency_p95"), 0.5):
        await notify("HIGH", f"Do p95 latency {m['latency_p95']:.3f}s > 0.50s", "/docs/operations/Runbooks.md#7-遅延スパイク対応")
    if within(m.get("slippage_p90"), 0.30):
        await notify("HIGH", f"p90 slippage {m['slippage_p90']:.2f}% > 0.30%", "/docs/operations/Runbooks.md#6-スリッページ急騰")
    if within(m.get("features_recency_s"), 120):
        await notify("MEDIUM", f"Features recency {m['features_recency_s']}s > 120s", "/docs/architecture/Plan-Layer.md#データ新鮮度")
    kpi = m.get("kpi") or {}
    if below(kpi.get("win_rate"), 0.50) or within(kpi.get("max_dd_pct"), 8.0):
        await notify("MEDIUM", f"KPI degradation win_rate={kpi.get('win_rate')} max_dd={kpi.get('max_dd_pct')}%", "/docs/models/Strategy-Lifecycle.md#降格条件")

def start_scheduler(loop):
    sch = AsyncIOScheduler(event_loop=loop, timezone="UTC")
    sch.add_job(poll_metrics, "interval", seconds=60, id="hud_alerts")
    sch.start()
    return sch
```

---

## 6. ログ（構造化 JSON）
**共通フィールド例**
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
- **Gunicorn 起動例（JSONアクセスログ）**
```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker \
  --workers 4 --log-level info \
  --access-logformat '{"ts":"%(t)s","ip":"%(h)s","method":"%(m)s","path":"%(U)s","status":"%(s)s","latency":"%(L)s","ref":"%(f)s","ua":"%(a)s"}' \
  --access-logfile -
```

---

## 7. HUD（ダッシュボード）設計
- **カード**：Do p95 レイテンシ / Do エラー率 / p90 スリッページ / 特徴量遅延 / KPI（win_rate・max_dd）  
- **時系列**：直近 10 分・1 時間の p95/p90 を折れ線で。  
- **注釈**：採用開始・段階移行・抑制ON/OFF・境界改訂は HUD 上部にトースト表示（Runbooks 連携）。  
- **SLO 表示**：各カードに SLO を併記。逸脱時に赤色・点滅などの視覚強調。

---

## 8. コスト & 保持
- **ログ**：標準出力（コンテナ基盤のログドライバまたは logrotate）。  
- **メトリクス**：Prometheus なしの場合、HUD 用の**短期（10分〜数時間）**のみ保持。  
- **監査**：`audit_order.json` は**WORM ストレージ**に長期保管（90日以上）。

---

## 9. 運用（アラートルーティング）
| 種別 | 送信先 | 付記 |
|---|---|---|
| CRITICAL | 電話/Pager（任意） + Slack | 24/7 当番 |
| HIGH | Slack `#ops-alerts` | 10 分ごと再通知 |
| MEDIUM | Slack `#ops` | 営業時間対応 |
| LOW | 週次レポート | 定例レビュー |

**抑制度合**：デプロイ直後/段階導入（7%→30%→100%）の 10 分は自動抑制。

---

## 10. Runbooks 連携（一次対応）
- `DoErrorBudgetBurn` → `Runbooks.md §8（ロールバック/停止→復帰）`  
- `DoLatencyP95High` → `Runbooks.md §7（遅延スパイク）`  
- `SlippageSpike` → `Runbooks.md §6（スリッページ）`  
- `PlanFeaturesStale` → `Plan-Layer.md §6（再収集/バックフィル）`  
- `KpiDegradation` → `Strategy-Lifecycle.md §4.5（降格/再評価）`

---

## 11. 実装統合メモ
- **FastAPI 立ち上げ**で `metrics.router` と `hud.router` を include。  
- **イベントループ取得**後に `alerts.start_scheduler(loop)` を呼ぶ。  
- **Correlation-ID 中継ミドルウェア**を入れて、各ログ/メトリクスへ付与。

**Correlation-ID（FastAPI ミドルウェア例）**
```python
# app/middleware/correlation.py
from uuid import uuid4
async def correlation_mw(request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response
```

---

## 12. 品質基準（DoD）
- HUD（/hud/observability）が**正しく表示**され、p95/p90/比率が更新される。  
- アラートが Slack に送れて、Runbooks 章へ**直リンク**できる。  
- 主要メトリクス・ログに `correlation_id` が入る。  
- 本書の SLO 値と実装のしきい値が**一致**（単一情報源）。

---

## 13. 変更履歴（Changelog）
- **2025-08-12**: **v1.1** Grafana 非依存の HUD 構成に刷新。APScheduler/Slack による内製アラートを追加。Prometheus あり/なしの二系統に対応。
- **2025-08-12**: v1.0 初版（PromQL 中心の記述）
