-- migrations/2025xxxx_add_outbox_orders.sql
-- Outbox パターンのための送信箱テーブル
BEGIN;

CREATE TABLE IF NOT EXISTS outbox_orders (
  id BIGSERIAL PRIMARY KEY,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  idempotency_key   TEXT NOT NULL UNIQUE,
  order_request_json JSONB NOT NULL,
  request_digest     TEXT NOT NULL,

  status            TEXT NOT NULL CHECK (status IN ('pending','sending','succeeded','failed','aborted')),
  attempts          INT NOT NULL DEFAULT 0,
  last_error_code   TEXT,
  last_error_msg    TEXT,

  locked_by         TEXT,
  locked_at         TIMESTAMPTZ,

  expires_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_outbox_status    ON outbox_orders (status);
CREATE INDEX IF NOT EXISTS idx_outbox_locked_at ON outbox_orders (locked_at);

COMMIT;
