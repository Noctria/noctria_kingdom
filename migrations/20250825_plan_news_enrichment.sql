-- =====================================================================
-- Noctria Kingdom — Plan News Enrichment Migration (2025-08-25)
-- 用途:
--   - ニュース/イベント可視化のための軽量スキーマ拡張とビュー作成。
--   - news_items に topic / entities(JSONB) / sentiment_score / event_tag を追加（再実行安全）。
--   - 可視化・特徴量で使うビュー:
--       * vw_news_daily_counts : 日次件数・平均感情・7日移動平均
--       * vw_news_event_tags   : タイトル/本文からの簡易イベントタグ推定（CPI/BOJ/FOMC/NFP）
-- =====================================================================

BEGIN;

-- 1) 追加カラム（存在しない場合のみ）
DO $$
BEGIN
  IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name='news_items' AND column_name='topic'
  ) THEN
    ALTER TABLE news_items ADD COLUMN topic TEXT;
  END IF;

  IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name='news_items' AND column_name='entities'
  ) THEN
    ALTER TABLE news_items ADD COLUMN entities JSONB;
  END IF;

  IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name='news_items' AND column_name='sentiment_score'
  ) THEN
    ALTER TABLE news_items ADD COLUMN sentiment_score REAL;
  END IF;

  IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name='news_items' AND column_name='event_tag'
  ) THEN
    ALTER TABLE news_items ADD COLUMN event_tag TEXT;
  END IF;
END$$;

-- 2) 日次集計ビュー（件数と平均感情、7日移動平均）
DROP VIEW IF EXISTS vw_news_daily_counts CASCADE;
CREATE VIEW vw_news_daily_counts AS
SELECT
  d.asset,
  d.date,
  d.cnt_1d,
  AVG(d.cnt_1d) OVER (
    PARTITION BY d.asset
    ORDER BY d.date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS cnt_7d_ma,
  d.senti_1d_avg,
  AVG(d.senti_1d_avg) OVER (
    PARTITION BY d.asset
    ORDER BY d.date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS senti_7d_avg
FROM (
  SELECT
    COALESCE(asset, 'USDJPY') AS asset,
    (published_at AT TIME ZONE 'UTC')::date AS date,
    COUNT(*) AS cnt_1d,
    AVG(sentiment_score) AS senti_1d_avg
  FROM news_items
  GROUP BY 1, 2
) AS d;

-- 3) 簡易イベント抽出ビュー（タイトル/本文/URLから event_tag を推定）
DROP VIEW IF EXISTS vw_news_event_tags CASCADE;
CREATE VIEW vw_news_event_tags AS
WITH base AS (
  SELECT
    id,
    COALESCE(asset, 'USDJPY') AS asset,
    (published_at AT TIME ZONE 'UTC')::date AS date,
    title,
    description,
    url,
    COALESCE(event_tag,
      CASE
        WHEN title ~* '\mCPI\M' OR description ~* '\mCPI\M' THEN 'CPI'
        WHEN title ~* '\mFOMC\M' OR description ~* '\mFOMC\M' THEN 'FOMC'
        WHEN title ~* '\mNFP\M|非農業' OR description ~* '\mNFP\M|非農業' THEN 'NFP'
        WHEN title ~* '\mBOJ\M|日銀' OR description ~* '\mBOJ\M|日銀' THEN 'BOJ'
        ELSE NULL
      END
    ) AS inferred_event_tag
  FROM news_items
)
SELECT *
FROM base
WHERE inferred_event_tag IS NOT NULL;

COMMIT;
