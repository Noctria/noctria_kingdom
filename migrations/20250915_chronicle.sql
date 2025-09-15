-- Royal Scribe / Chronicle schema
CREATE TABLE IF NOT EXISTS chronicle_thread (
  id BIGSERIAL PRIMARY KEY,
  topic TEXT NOT NULL,         -- 例: "PDCA nightly", "Veritas backtest", "Incident-2025-09-15"
  tags  TEXT[],                -- 例: '{pdca, nightly, veritas}'
  started_at timestamptz NOT NULL DEFAULT now(),
  is_open BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS chronicle_entry (
  id BIGSERIAL PRIMARY KEY,
  thread_id BIGINT REFERENCES chronicle_thread(id),
  trace_id TEXT,
  ts timestamptz NOT NULL DEFAULT now(),
  title TEXT NOT NULL,
  category TEXT NOT NULL,      -- decision|patch|kpi|pr|deploy|incident|note|retro|order
  content_md TEXT NOT NULL,    -- Markdown 本文（要約・決定・根拠）
  refs JSONB
);

CREATE INDEX IF NOT EXISTS idx_chronicle_thread_topic ON chronicle_thread(topic);
CREATE INDEX IF NOT EXISTS idx_chronicle_entry_trace ON chronicle_entry(trace_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_chronicle_entry_cat   ON chronicle_entry(category, ts DESC);
