# 4) scripts/init_obs_schema.sql
```sql
-- 初期化SQL: psql などで適用
--   psql "$NOCTRIA_OBS_PG_DSN" -f scripts/init_obs_schema.sql
CREATE TABLE IF NOT EXISTS obs_plan_runs (
  id           BIGSERIAL PRIMARY KEY,
  trace_id     TEXT NOT NULL,
  component    TEXT NOT NULL,
  status       TEXT NOT NULL,
  started_at   TIMESTAMPTZ NOT NULL,
  finished_at  TIMESTAMPTZ,
  duration_ms  INTEGER,
  metrics      JSONB DEFAULT '{}'::jsonb,
  tags         TEXT[] DEFAULT '{}',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obs_plan_runs_trace_id ON obs_plan_runs (trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_plan_runs_started ON obs_plan_runs (started_at);
CREATE INDEX IF NOT EXISTS idx_obs_plan_runs_comp   ON obs_plan_runs (component);

CREATE TABLE IF NOT EXISTS obs_infer_calls (
  id           BIGSERIAL PRIMARY KEY,
  trace_id     TEXT NOT NULL,
  model_name   TEXT NOT NULL,
  latency_ms   INTEGER,
  input_size   INTEGER,
  success      BOOLEAN NOT NULL DEFAULT TRUE,
  extra        JSONB DEFAULT '{}'::jsonb,
  called_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obs_infer_calls_trace_id ON obs_infer_calls (trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_infer_calls_called   ON obs_infer_calls (called_at);
CREATE INDEX IF NOT EXISTS idx_obs_infer_calls_model    ON obs_infer_calls (model_name);
```
