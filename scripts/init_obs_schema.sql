-- scripts/init_obs_schema.sql
-- Noctria Observability schema (PostgreSQL 12+)

-- =========================
-- Tables
-- =========================
CREATE TABLE IF NOT EXISTS obs_plan_runs (
  id             BIGSERIAL PRIMARY KEY,
  ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- legacy (phase-level)
  phase          TEXT,
  dur_sec        INTEGER,
  rows           INTEGER,
  missing_ratio  REAL,
  error_rate     REAL,
  -- span-level
  trace_id       TEXT,
  started_at     TIMESTAMPTZ,
  finished_at    TIMESTAMPTZ,
  status         TEXT,
  meta           JSONB
);
CREATE INDEX IF NOT EXISTS idx_plan_runs_ts    ON obs_plan_runs(ts);
CREATE INDEX IF NOT EXISTS idx_plan_runs_trace ON obs_plan_runs(trace_id);

CREATE TABLE IF NOT EXISTS obs_infer_calls (
  id                     BIGSERIAL PRIMARY KEY,
  ts                     TIMESTAMPTZ NOT NULL DEFAULT now(),
  model                  TEXT,
  ver                    TEXT,
  dur_ms                 INTEGER,
  success                BOOLEAN,
  feature_staleness_min  INTEGER,
  trace_id               TEXT,
  -- new
  model_name             TEXT,
  call_at                TIMESTAMPTZ,
  duration_ms            INTEGER,
  inputs                 JSONB,
  outputs                JSONB
);
CREATE INDEX IF NOT EXISTS idx_infer_calls_ts    ON obs_infer_calls(ts);
CREATE INDEX IF NOT EXISTS idx_infer_calls_trace ON obs_infer_calls(trace_id);
CREATE INDEX IF NOT EXISTS idx_infer_calls_model ON obs_infer_calls(model_name);

CREATE TABLE IF NOT EXISTS obs_decisions (
  id              BIGSERIAL PRIMARY KEY,
  trace_id        TEXT NOT NULL,
  made_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  engine_version  TEXT,
  strategy_name   TEXT,
  score           NUMERIC,
  reason          TEXT,
  features        JSONB,
  decision        JSONB
);
CREATE INDEX IF NOT EXISTS idx_decisions_trace ON obs_decisions(trace_id);
CREATE INDEX IF NOT EXISTS idx_decisions_made  ON obs_decisions(made_at);

CREATE TABLE IF NOT EXISTS obs_exec_events (
  id        BIGSERIAL PRIMARY KEY,
  trace_id  TEXT NOT NULL,
  sent_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  symbol    TEXT,
  side      TEXT,
  size      NUMERIC,
  provider  TEXT,
  status    TEXT,
  order_id  TEXT,
  response  JSONB
);
CREATE INDEX IF NOT EXISTS idx_exec_events_trace ON obs_exec_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_exec_events_sent  ON obs_exec_events(sent_at);

CREATE TABLE IF NOT EXISTS obs_alerts (
  id          BIGSERIAL PRIMARY KEY,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  policy_name TEXT NOT NULL,
  reason      TEXT NOT NULL,
  severity    TEXT NOT NULL,
  details     JSONB,
  trace_id    TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_trace ON obs_alerts(trace_id);
CREATE INDEX IF NOT EXISTS idx_alerts_time  ON obs_alerts(created_at);

-- =========================
-- Views
-- =========================
CREATE OR REPLACE VIEW obs_trace_timeline AS
SELECT trace_id, made_at AS ts, 'DECISION' AS kind,
       decision->>'action' AS action, decision AS payload
FROM obs_decisions
UNION ALL
SELECT trace_id, sent_at AS ts, 'EXEC' AS kind,
       side AS action,
       jsonb_build_object('size', size, 'provider', provider, 'status', status, 'order_id', order_id, 'response', response) AS payload
FROM obs_exec_events
UNION ALL
SELECT trace_id, COALESCE(call_at, ts) AS ts, 'INFER' AS kind,
       COALESCE(model_name, model) AS action,
       jsonb_build_object('duration_ms', COALESCE(duration_ms, dur_ms), 'success', success, 'inputs', inputs, 'outputs', outputs) AS payload
FROM obs_infer_calls
UNION ALL
SELECT trace_id, COALESCE(started_at, ts) AS ts, 'PLAN:'||COALESCE(status,'phase') AS kind,
       COALESCE(phase,'') AS action,
       jsonb_build_object('rows', rows, 'missing_ratio', missing_ratio, 'error_rate', error_rate, 'meta', meta) AS payload
FROM obs_plan_runs
UNION ALL
SELECT trace_id, created_at AS ts, 'ALERT' AS kind,
       COALESCE(policy_name,'') AS action,
       jsonb_build_object('reason', reason, 'severity', severity, 'details', details) AS payload
FROM obs_alerts;

CREATE OR REPLACE VIEW obs_trace_latency AS
WITH t AS (
  SELECT trace_id, ts, kind FROM obs_trace_timeline
),
agg AS (
  SELECT
    trace_id,
    MIN(CASE WHEN kind='PLAN:START' THEN ts END) AS plan_start,
    MIN(CASE WHEN kind='INFER'      THEN ts END) AS infer_ts,
    MIN(CASE WHEN kind='DECISION'   THEN ts END) AS decision_ts,
    MIN(CASE WHEN kind='EXEC'       THEN ts END) AS exec_ts
  FROM t
  GROUP BY trace_id
)
SELECT
  trace_id,
  plan_start, infer_ts, decision_ts, exec_ts,
  EXTRACT(EPOCH FROM (infer_ts    - plan_start))*1000  AS ms_plan_to_infer,
  EXTRACT(EPOCH FROM (decision_ts - infer_ts))*1000    AS ms_infer_to_decision,
  EXTRACT(EPOCH FROM (exec_ts     - decision_ts))*1000 AS ms_decision_to_exec,
  EXTRACT(EPOCH FROM (exec_ts     - plan_start))*1000  AS ms_total
FROM agg;

-- =========================
-- Materialized View
-- =========================
CREATE MATERIALIZED VIEW IF NOT EXISTS obs_latency_daily AS
SELECT
  date_trunc('day', plan_start)::date AS day,
  percentile_cont(0.5)  WITHIN GROUP (ORDER BY ms_total) AS p50_ms,
  percentile_cont(0.9)  WITHIN GROUP (ORDER BY ms_total) AS p90_ms,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY ms_total) AS p95_ms,
  MAX(ms_total) AS max_ms,
  COUNT(*)      AS traces
FROM obs_trace_latency
GROUP BY 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_obs_latency_daily_day ON obs_latency_daily(day);
