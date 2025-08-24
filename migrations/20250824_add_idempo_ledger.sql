-- migrations/20250824_add_idempo_ledger.sql
-- Idempotency Ledger (OrderRequest v1.1) — Postgres

BEGIN;

CREATE TABLE IF NOT EXISTS idempo_ledger (
  idempotency_key       TEXT PRIMARY KEY,
  request_digest        TEXT NOT NULL,
  result_digest         TEXT,
  status                TEXT NOT NULL CHECK (status IN ('accepted','succeeded','failed')),
  first_seen_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at            TIMESTAMPTZ NOT NULL,
  response_payload_json JSONB,
  http_status           INT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idempo_ledger_expires
  ON idempo_ledger (expires_at);

COMMIT;
