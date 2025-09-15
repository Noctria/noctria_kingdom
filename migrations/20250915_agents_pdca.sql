-- Agent/PDCA logging schema
CREATE TABLE IF NOT EXISTS agent_run (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT UNIQUE,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  status TEXT,               -- RUNNING / SUCCESS / FAIL
  notes  TEXT
);

CREATE TABLE IF NOT EXISTS agent_message (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,    -- agent_run.trace_id に紐づけ
  agent   TEXT NOT NULL,     -- inventor / harmonia / veritas / hermes / orchestrator
  role    TEXT NOT NULL,     -- system / user / assistant / tool
  content TEXT NOT NULL,     -- 平文（短文OK）
  meta    JSONB,
  ts      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_message_trace ON agent_message(trace_id, ts DESC);

CREATE TABLE IF NOT EXISTS build_artifact (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  kind TEXT NOT NULL,        -- patch / report / model / kpi
  path TEXT,
  payload JSONB,
  ts timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS test_result (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  total INT, passed INT, failed INT, errors INT, skipped INT,
  junit_xml_path TEXT,
  raw JSONB,
  ts timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lint_result (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  errors INT, warnings INT,
  ruff_json_path TEXT,
  raw JSONB,
  ts timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS git_commit_log (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  branch TEXT NOT NULL,
  sha TEXT,
  files JSONB,
  message TEXT,
  ts timestamptz NOT NULL DEFAULT now()
);
