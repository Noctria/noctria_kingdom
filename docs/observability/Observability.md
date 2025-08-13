# 👁️ Observability.md  
_Noctria Kingdom — 観測・可視化ガイド（最新版 / 2025-08-14）_

本ドキュメントは **PDCA 可観測性（Observability）** の決定事項・実装仕様（DBスキーマ/ビュー、GUI ルート、運用手順）を **単体で完結** するようにまとめています。  
最新 GUI 実装は **`/pdca/timeline`**（時系列ビュー）と **`/pdca/latency/daily`**（日次レイテンシ）です。

---

## 0. TL;DR（確定事項）
- **対象範囲**: GUI (FastAPI)／Plan／Infer（AI）／Decision／Exec／Alert を **trace_id で貫通**して記録・集約。
- **保存先（最小コア）**:  
  - **イベント集約 VIEW**: `obs_trace_timeline`（GUI の時系列）  
  - **レイテンシ VIEW**: `obs_trace_latency`（Plan→Infer→Decision→Exec の相対時差）  
  - **日次レイテンシ MVIEW**: `obs_latency_daily`（p50/p90/p95/max/traces）
- **GUI ルート**:  
  - `GET /pdca/timeline`（trace 列挙 or 1 トレース時系列）  
  - `GET /pdca/latency/daily`（直近 30 日の p50/p90/p95/max）  
  - `POST /pdca/observability/refresh`（ビュー確保・MV 更新）
- **運用**: systemd + Gunicorn（UvicornWorker）。**ENV** で DSN/PORT を注入。  
  - `/etc/default/noctria-gui` … `NOCTRIA_OBS_PG_DSN` / `NOCTRIA_GUI_PORT`
- **保持**: 原始イベントは 30 日→日次ロールアップ（MV 参照で OK）。

---

## 1. 目的と非目的
### 1.1 目的
- **運用判断に必要な最小指標**（フェーズ間レイテンシ、イベント時系列、アラート）を **E2E trace** で可視化。
- **DB 中心**の SoT（Source of Truth）化：SQL ビューで GUI と疎結合に。

### 1.2 非目的
- APM/Grafana の代替ではない（外部通知やメトリクス収集は最小限）。
- 全機能 KPI ダッシュボードではない（必要最小の **PDCA 監視** に限定）。

---

## 2. イベントモデル（最小コア）
**イベントは “同一 trace_id” で Plan→Infer→Decision→Exec→Alert を貫通**。  
GUI 時系列は **`kind`**（PLAN/INFER/DECISION/EXEC/ALERT）＋`action/payload` を整形表示。

### 2.1 共通カラム（推奨）
- `ts TIMESTAMPTZ`（UTC 固定）
- `trace_id TEXT`
- `kind TEXT` （`PLAN:START` / `PLAN:END` / `INFER` / `DECISION` / `EXEC` / `ALERT` など）
- `action TEXT NULL`（モデル名/戦略名/ポリシー名等）
- `payload JSONB NULL`（任意の付帯データ）

> 実テーブルはチーム/層ごとに分かれていて OK（例: `obs_plan_runs`, `obs_infer_calls`, `obs_decisions`, `obs_exec_events`, `obs_alerts`）。  
> 本ドキュメントでは **ビュー**で GUI に提供する形を標準とする。

---

## 3. DDL（テーブル最小 & ビュー/MV 定義）
> そのまま psql に貼り付け可能な最小構成。既存テーブルがある場合は CREATE IF NOT EXISTS で追記してください。

```sql
-- =========================================
-- 3.1 最小イベントテーブル（サンプル構成）
-- =========================================

-- Plan フェーズ（開始/終了や処理統計）
CREATE TABLE IF NOT EXISTS obs_plan_runs (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  trace_id TEXT NOT NULL,
  phase TEXT NOT NULL,                   -- "PLAN:START" | "PLAN:END" など
  action TEXT,
  payload JSONB
);
CREATE INDEX IF NOT EXISTS idx_obs_plan_runs_ts ON obs_plan_runs(ts);
CREATE INDEX IF NOT EXISTS idx_obs_plan_runs_trace ON obs_plan_runs(trace_id);

-- 推論（モデル名・バージョン・所要時間など）
CREATE TABLE IF NOT EXISTS obs_infer_calls (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  trace_id TEXT NOT NULL,
  model TEXT,
  ver TEXT,
  dur_ms INT,
  success BOOLEAN,
  payload JSONB
);
CREATE INDEX IF NOT EXISTS idx_obs_infer_calls_ts ON obs_infer_calls(ts);
CREATE INDEX IF NOT EXISTS idx_obs_infer_calls_trace ON obs_infer_calls(trace_id);

-- 決定（王の決定 / ルール選択 / 重み等）
CREATE TABLE IF NOT EXISTS obs_decisions (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  trace_id TEXT NOT NULL,
  action TEXT,                           -- 例: "BUY" / "FLAT" / "scalp" 等
  confidence DOUBLE PRECISION,
  payload JSONB
);
CREATE INDEX IF NOT EXISTS idx_obs_decisions_ts ON obs_decisions(ts);
CREATE INDEX IF NOT EXISTS idx_obs_decisions_trace ON obs_decisions(trace_id);

-- 実行（注文/実行の要約イベント）
CREATE TABLE IF NOT EXISTS obs_exec_events (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  trace_id TEXT NOT NULL,
  action TEXT,                           -- 例: "MARKET", "LIMIT", "CANCELLED"
  status TEXT,                           -- 例: "SENT", "ACCEPTED", "FILLED", "REJECTED"
  payload JSONB
);
CREATE INDEX IF NOT EXISTS idx_obs_exec_events_ts ON obs_exec_events(ts);
CREATE INDEX IF NOT EXISTS idx_obs_exec_events_trace ON obs_exec_events(trace_id);

-- アラート（リスク/品質/逸脱）
CREATE TABLE IF NOT EXISTS obs_alerts (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  trace_id TEXT,
  severity TEXT,                         -- Info/Warning/Critical
  action TEXT,                           -- アラートキー（例: "risk.max_order_qty"）
  payload JSONB
);
CREATE INDEX IF NOT EXISTS idx_obs_alerts_ts ON obs_alerts(ts);
CREATE INDEX IF NOT EXISTS idx_obs_alerts_trace ON obs_alerts(trace_id);

-- =========================================
-- 3.2 タイムライン VIEW（GUI /pdca/timeline が参照）
-- =========================================

CREATE OR REPLACE VIEW obs_trace_timeline AS
WITH plan AS (
  SELECT ts, trace_id, phase      AS kind, action, payload FROM obs_plan_runs
),
infer AS (
  SELECT ts, trace_id, 'INFER'    AS kind, model AS action,
         jsonb_build_object('ver', ver, 'dur_ms', dur_ms, 'success', success) || coalesce(payload,'{}'::jsonb) AS payload
  FROM obs_infer_calls
),
decision AS (
  SELECT ts, trace_id, 'DECISION' AS kind, action,
         jsonb_build_object('confidence', confidence) || coalesce(payload,'{}'::jsonb) AS payload
  FROM obs_decisions
),
exec AS (
  SELECT ts, trace_id, 'EXEC'     AS kind, coalesce(status, action) AS action, payload
  FROM obs_exec_events
),
alert AS (
  SELECT ts, coalesce(trace_id,'') AS trace_id, 'ALERT' AS kind, action,
         jsonb_build_object('severity', severity) || coalesce(payload,'{}'::jsonb) AS payload
  FROM obs_alerts
)
SELECT * FROM plan
UNION ALL SELECT * FROM infer
UNION ALL SELECT * FROM decision
UNION ALL SELECT * FROM exec
UNION ALL SELECT * FROM alert;

-- =========================================
-- 3.3 トレース別レイテンシ VIEW
--     （Plan→Infer→Decision→Exec の代表時刻と差分）
-- =========================================

CREATE OR REPLACE VIEW obs_trace_latency AS
WITH agg AS (
  SELECT
    trace_id,
    MIN(CASE WHEN kind LIKE 'PLAN:%' THEN ts END)     AS plan_start,
    MIN(CASE WHEN kind = 'INFER'     THEN ts END)     AS infer_ts,
    MIN(CASE WHEN kind = 'DECISION'  THEN ts END)     AS decision_ts,
    MIN(CASE WHEN kind = 'EXEC'      THEN ts END)     AS exec_ts
  FROM obs_trace_timeline
  GROUP BY trace_id
)
SELECT
  trace_id,
  plan_start,
  infer_ts,
  decision_ts,
  exec_ts,
  ROUND(EXTRACT(EPOCH FROM (infer_ts    - plan_start))*1000.0, 3) AS ms_plan_to_infer,
  ROUND(EXTRACT(EPOCH FROM (decision_ts - infer_ts  ))*1000.0, 3) AS ms_infer_to_decision,
  ROUND(EXTRACT(EPOCH FROM (exec_ts     - decision_ts))*1000.0, 3) AS ms_decision_to_exec,
  ROUND(EXTRACT(EPOCH FROM (exec_ts     - plan_start))*1000.0, 3) AS ms_total
FROM agg
WHERE plan_start IS NOT NULL
ORDER BY exec_ts DESC NULLS LAST;

-- =========================================
-- 3.4 日次レイテンシ MATERIALIZED VIEW（GUI /pdca/latency/daily）
-- =========================================

CREATE MATERIALIZED VIEW IF NOT EXISTS obs_latency_daily AS
SELECT
  DATE_TRUNC('day', plan_start)::date AS day,
  PERCENTILE_DISC(0.50) WITHIN GROUP (ORDER BY ms_total) AS p50_ms,
  PERCENTILE_DISC(0.90) WITHIN GROUP (ORDER BY ms_total) AS p90_ms,
  PERCENTILE_DISC(0.95) WITHIN GROUP (ORDER BY ms_total) AS p95_ms,
  MAX(ms_total) AS max_ms,
  COUNT(*) AS traces
FROM obs_trace_latency
WHERE plan_start IS NOT NULL
GROUP BY 1
ORDER BY 1 DESC;

CREATE INDEX IF NOT EXISTS idx_obs_latency_daily_day ON obs_latency_daily(day);
```

> 備考: `obs_trace_latency` は **代表 1 イベント/フェーズ** を最小時刻で採る素朴定義です。複数回/再試行がある場合は要件（最新/最小/最大など）で調整。

---

## 4. GUI 仕様（FastAPI + Jinja2）
- ルータ: `noctria_gui/routes/observability.py`  
  - DSN は `NOCTRIA_OBS_PG_DSN`（例: `postgresql://noctria:noctria@127.0.0.1:55432/noctria_db`）
  - **テンプレート**:
    - `templates/pdca_timeline.html` … trace 一覧 or 1 トレース時系列（色分け pill）
    - `templates/pdca_latency_daily.html` … 直近 30 日の p50/p90/p95/max/traces
- ルート:
  - `GET /pdca/timeline?trace=<trace_id>&days=3&limit=200`  
  - `GET /pdca/latency/daily`  
  - `POST /pdca/observability/refresh`

---

## 5. 運用（systemd + Gunicorn）
**環境ファイル** `/etc/default/noctria-gui`（LF・644・root:root）
```
NOCTRIA_OBS_PG_DSN=postgresql://noctria:noctria@127.0.0.1:55432/noctria_db
NOCTRIA_GUI_PORT=8001
```

**ユニット** `/etc/systemd/system/noctria_gui.service`（抜粋）
```
[Service]
User=noctria
Group=noctria
WorkingDirectory=/mnt/d/noctria_kingdom
EnvironmentFile=/etc/default/noctria-gui
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/mnt/d/noctria_kingdom
ExecStart=/bin/sh -lc 'exec /mnt/d/noctria_kingdom/venv_gui/bin/gunicorn \
  --workers 4 --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${NOCTRIA_GUI_PORT:-8001} \
  --access-logfile - --error-logfile - \
  noctria_gui.main:app'
Restart=always
RestartSec=3
```

**確認コマンド**
```
sudo systemctl daemon-reload && sudo systemctl restart noctria_gui
sudo systemctl show -p EnvironmentFiles -p Environment -p ExecStart noctria_gui
ss -ltnp | grep ':8001'
curl -sS http://127.0.0.1:${NOCTRIA_GUI_PORT:-8001}/healthz
```

---

## 6. データ保持とロールアップ
- **原始イベント**（各 `obs_*` テーブル）: 30 日保持（パーティション/TTL/ロールアップは運用ポリシーに準拠）  
- **`obs_latency_daily`**: 過去分を保持（SELECT 対象は直近 30 日で十分）  
- 将来: `obs_trace_timeline` を **MVIEW 化**する場合は `CONCURRENTLY` リフレッシュ戦略を検討。

---

## 7. しきい値（参考・最小セット）
- **レイテンシ（ms_total, p95）**: 10,000ms 超で **Warning**、15,000ms 超で **Critical**  
- **Exec 失敗率（当日）**: 1% 超で Warning、3% 超で Critical  
- アラートは `obs_alerts` に書き、GUI で軽量表示（外部通知は当面なし）。

---

## 8. 動作確認（サンプルデータ投入）
```sql
-- 1 トレースの最低限イベント
WITH t AS (SELECT 'smoke-1'::text AS trace_id)
INSERT INTO obs_plan_runs(ts, trace_id, phase, action, payload)
SELECT now() - interval '20 s', trace_id, 'PLAN:START', NULL, '{}'::jsonb FROM t
UNION ALL SELECT now() - interval '10 s', trace_id, 'PLAN:END', NULL, '{}'::jsonb FROM t;

INSERT INTO obs_infer_calls(ts, trace_id, model, ver, dur_ms, success, payload)
VALUES (now() - interval '9 s', 'smoke-1', 'DummyModel', 'v0', 1200, true, '{}');

INSERT INTO obs_decisions(ts, trace_id, action, confidence, payload)
VALUES (now() - interval '8 s', 'smoke-1', 'BUY', 0.62, '{}');

INSERT INTO obs_exec_events(ts, trace_id, action, status, payload)
VALUES (now() - interval '7 s', 'smoke-1', 'MARKET', 'FILLED', '{"qty":1000,"price":1.2345}');

-- 確認
SELECT * FROM obs_trace_timeline WHERE trace_id='smoke-1' ORDER BY ts;
SELECT * FROM obs_trace_latency  WHERE trace_id='smoke-1';
REFRESH MATERIALIZED VIEW obs_latency_daily;
SELECT * FROM obs_latency_daily ORDER BY day DESC LIMIT 5;
```

---

## 9. Mermaid（構成図・概要）※GitHub でレンダリング可

```mermaid
flowchart LR
  P["Plan: obs_plan_runs"] --> T["obs_trace_timeline"]
  I["Infer: obs_infer_calls"] --> T
  D["Decision: obs_decisions"] --> T
  E["Exec: obs_exec_events"] --> T
  A["Alert: obs_alerts"] --> T

  T --> L["obs_trace_latency"]
  L --> M["obs_latency_daily"]

  subgraph GUI_FastAPI["GUI (FastAPI)"]
    TL["GET /pdca/timeline/"] -->|SELECT| T
    LD["GET /pdca/latency/daily"] -->|SELECT| M
    RF["POST /pdca/observability/refresh"] -->|ensure_views + REFRESH| M
  end
```

---

## 10. 変更履歴
- **2025-08-14**:  
  - GUI 実装に合わせ **`/pdca/timeline` / `/pdca/latency/daily` / `POST /pdca/observability/refresh`** を正式化。  
  - **`obs_trace_timeline` / `obs_trace_latency` / `obs_latency_daily`** の DDL を一本化。  
  - Mermaid 図を **GitHub 互換の形** に修正（特殊シェイプ/エスケープの排除、`subgraph` 表記の正規化）。  
- **2025-08-12**: 初版（HUD 方針は撤回、PDCA 直下へ集約）。
