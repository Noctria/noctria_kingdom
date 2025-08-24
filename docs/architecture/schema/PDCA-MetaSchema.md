# PDCA Meta Schema — 戦略メタ/結果/しきい値/成果物
**Last Updated:** 2025-08-24 (JST)  
**Owner:** PDCA / Data Platform

関連文書:
- `docs/apis/PDCA-Recheck-API-Spec.md`
- `docs/airflow/DAG-PDCA-Recheck.md`
- `docs/observability/DoLayer-Metrics.md`

---

## 0. 目的
PDCA 再チェックの対象解決・結果保存・可視化に必要な**メタデータ層**のスキーマを定義する。  
GUI はこのスキーマを前提に一覧・検索・レポートを行う。

---

## 1. エンティティ概要
- **strategies**: 戦略の基本メタ（ID・状態・タグ・属性）
- **strategy_tags**: 戦略とタグの多対多
- **pdca_results**: 再チェック結果（各リクエスト×戦略×期間）
- **threshold_profiles**: KPI しきい値セット（環境/銘柄別に切替）
- **artifacts**: 生成成果物（レポート/画像/CSV 等）メタ
- **pdca_requests** *(任意)*: リクエスト受付のSoT（Airflow連携用の索引）

---

## 2. DDL（PostgreSQL 例）

### 2.1 strategies
```sql
CREATE TABLE IF NOT EXISTS strategies (
  id               TEXT PRIMARY KEY,             -- e.g. 'strat.meanrev.m1'
  title            TEXT NOT NULL,
  instrument       TEXT NOT NULL,                -- 'USDJPY' など
  owner            TEXT,                         -- 担当者/チーム
  health           TEXT NOT NULL DEFAULT 'unknown' CHECK (health IN ('healthy','degraded','unknown')),
  enabled          BOOLEAN NOT NULL DEFAULT TRUE,
  metadata_json    JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_strategies_instrument ON strategies (instrument);
CREATE INDEX IF NOT EXISTS idx_strategies_health ON strategies (health);
```

### 2.2 strategy_tags
```sql
CREATE TABLE IF NOT EXISTS strategy_tags (
  strategy_id      TEXT NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
  tag              TEXT NOT NULL,
  PRIMARY KEY (strategy_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_strategy_tags_tag ON strategy_tags (tag);
```

### 2.3 pdca_requests *(任意)*
```sql
CREATE TABLE IF NOT EXISTS pdca_requests (
  request_id       TEXT PRIMARY KEY,             -- ULID
  kind             TEXT NOT NULL CHECK (kind IN ('single','bulk')),
  client_id        TEXT NOT NULL,
  reason           TEXT,
  params_json      JSONB NOT NULL DEFAULT '{}'::jsonb,
  submitted_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.4 pdca_results
```sql
CREATE TABLE IF NOT EXISTS pdca_results (
  id               BIGSERIAL PRIMARY KEY,
  request_id       TEXT NOT NULL,                -- pdca_requests.request_id（任意参照）
  strategy_id      TEXT NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
  window_from      TIMESTAMPTZ NOT NULL,
  window_to        TIMESTAMPTZ NOT NULL,
  metrics_json     JSONB NOT NULL,               -- {sharpe,winrate,max_dd,...}
  health           TEXT NOT NULL CHECK (health IN ('healthy','degraded','unknown')),
  result_digest    TEXT NOT NULL,                -- 正規化→SHA-256
  completed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (request_id, strategy_id)               -- 同一リクエストで重複保存を抑止
);
CREATE INDEX IF NOT EXISTS idx_pdca_results_strategy_time
  ON pdca_results (strategy_id, completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdca_results_health
  ON pdca_results (health);
```

### 2.5 threshold_profiles
```sql
CREATE TABLE IF NOT EXISTS threshold_profiles (
  profile_id       TEXT PRIMARY KEY,             -- 'default', 'fx.usdjpy', etc.
  description      TEXT,
  rules_json       JSONB NOT NULL,               -- 例: {"winrate":{"op":">=","value":0.52}, ...}
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- strategies への割当（任意）
CREATE TABLE IF NOT EXISTS strategy_threshold_binding (
  strategy_id      TEXT NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
  profile_id       TEXT NOT NULL REFERENCES threshold_profiles(profile_id) ON DELETE CASCADE,
  PRIMARY KEY (strategy_id)
);
```

### 2.6 artifacts
```sql
CREATE TABLE IF NOT EXISTS artifacts (
  id               BIGSERIAL PRIMARY KEY,
  request_id       TEXT NOT NULL,
  strategy_id      TEXT NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
  kind             TEXT NOT NULL,                -- 'chart','report','csv' など
  url              TEXT NOT NULL,                -- 署名付きURL or 相対パス
  content_type     TEXT,
  bytes_size       BIGINT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_artifacts_strategy_time
  ON artifacts (strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifacts_request
  ON artifacts (request_id);
```

---

## 3. ビュー/マテビュー（ダッシュボード用）

### 3.1 最新健康状態ビュー
```sql
CREATE VIEW vw_strategy_latest_health AS
SELECT s.id, s.title, s.instrument, s.enabled,
       r.health AS last_health,
       r.completed_at AS last_checked_at
FROM strategies s
LEFT JOIN LATERAL (
  SELECT health, completed_at
    FROM pdca_results pr
   WHERE pr.strategy_id = s.id
   ORDER BY completed_at DESC
   LIMIT 1
) r ON TRUE;
```

### 3.2 直近ウィンドウのKPI要約（マテビュー例）
```sql
CREATE MATERIALIZED VIEW mv_pdca_recent_summary AS
SELECT strategy_id,
       count(*) AS runs,
       avg( (metrics_json->>'sharpe')::float ) AS sharpe_avg,
       avg( (metrics_json->>'winrate')::float ) AS winrate_avg,
       max(completed_at) AS last_completed_at
FROM pdca_results
WHERE completed_at >= now() - interval '30 days'
GROUP BY strategy_id;
```

---

## 4. 一貫性と制約
- `pdca_results.window_from <= window_to` をアプリ層で保証  
- `result_digest` は**安定キー**のみから生成（変動の大きいメタは除外）  
- `threshold_profiles.rules_json` の検証は API/DAG 側で行う（未知の指標は拒否）

---

## 5. 典型クエリ

### 5.1 GUI 一覧（最新ヘルス）
```sql
SELECT * FROM vw_strategy_latest_health
ORDER BY enabled DESC, last_checked_at DESC NULLS LAST
LIMIT 100 OFFSET 0;
```

### 5.2 フィルタ：タグ + 健康状態 + 銘柄
```sql
SELECT s.*
FROM strategies s
JOIN strategy_tags t ON t.strategy_id = s.id
JOIN vw_strategy_latest_health v ON v.id = s.id
WHERE t.tag = ANY($1)            -- tags_any
  AND v.last_health = ANY($2)    -- health[]
  AND s.instrument = ANY($3);    -- instrument_any[]
```

### 5.3 指定期間の結果閲覧
```sql
SELECT *
FROM pdca_results
WHERE strategy_id = $1
  AND completed_at BETWEEN $2 AND $3
ORDER BY completed_at DESC
LIMIT 200;
```

---

## 6. 移行と初期データ
- 初期挿入例（しきい値プロファイル）
```sql
INSERT INTO threshold_profiles(profile_id, description, rules_json) VALUES
('default', '標準しきい値', '{
  "winrate": {"op": ">=", "value": 0.52},
  "sharpe":  {"op": ">=", "value": 0.80},
  "max_dd":  {"op": "<=", "value": 0.10}
}');
```
- 既存戦略に `strategy_threshold_binding` でプロファイル割当

---

## 7. 可観測性（スキーマ視点）
- メトリクス候補:
  - `pdca.results_writes_total`
  - `pdca.artifacts_writes_total`
  - `pdca.strategies_enabled_count`
- 監査:
  - `pdca_requests` を SoT にすると **API 受理 → DAG 実行** の追跡が容易

---

## 8. 変更履歴
- **2025-08-24**: 初版
