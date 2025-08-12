# Observability.md
_Noctria Kingdom — 観測・可視化ガイド（最新版 / 2025-08-12）_

本ドキュメントは `/hud/observability` および関連ETL/計測の**決定事項**を一問一答の結果に基づき集約したものです。未決事項は「要検討」と明記します。

---

## 0. TL;DR（確定事項）
- **対象範囲**: A) FastAPI（GUI）, C) 学習/推論, D) 戦略実行, E) Plan層（collector/features/statistics）
- **収集/保存**: a) アプリ内計測→DB, c) Airflowタスク集約, d) ログETL集約
- **計測仕込み（要点）**  
  - A: ASGIミドルウェア＋例外ハンドラ＋テンプレ描画計測  
  - C: 学習ループ, モデル保存直後, 推論の入口/出口, 特徴量変換完了  
  - D: 注文発行前後, 約定イベント, リスクチェック前後, 日次/戦略単位集計  
  - E: collector, features, statistics の開始/終了＋異常検知
- **保存先テーブル**: `obs_api_requests`, `obs_train_jobs`, `obs_infer_calls`, `obs_orders`, `obs_trades`, `obs_plan_runs`, `obs_alerts`（全採用）
- **保持期間**: 生データ30日→日次ロールアップ、重要KPI180日、アラート90日（Criticalは180日）
- **アラート閾値**: 下記 §6 に定義（採用）
- **通知チャネル**: GUI内バナーのみ（外部通知なし）
- **ETL頻度/方式**: 5分ごと / AirflowのETL DAGで集約
- **権限**: 全員閲覧可（ログイン不要）
- **HUDレイアウト**: **要検討（保留）**

---

## 1. 目的と非目的
### 1.1 目的
- 運用判断に必要な**レイテンシ/エラー/学習精度/執行KPI/データ品質**の一元可視化
- 事後解析のための**最低限の生ログ**と**集約KPI**の確保
- PDCAにおける **Plan→Do→Check** の循環を支える観測基盤

### 1.2 非目的
- フル機能のAPMや外部ダッシュボード（Grafana等）の代替は目指さない
- 高頻度の外部通知（Slack/Email）— 今回は採用しない

---

## 2. 対象コンポーネント（Scope）
- **A. FastAPI（GUI）**
- **C. 学習/推論（例: Prometheus Oracle）**
- **D. 戦略実行（オーダー執行・リスク監視）**
- **E. Plan層（collector / features / statistics）**

---

## 3. メトリクス・KPI（推奨セット）
### 3.1 A: FastAPI（GUI）
- `http_requests_total`（メソッド/パス）
- `http_request_duration_ms`（p50/p90/p99）
- `http_error_rate`（4xx/5xx）
- `template_render_time_ms`（Jinja描画）
- `process_cpu_percent`, `process_rss_mb`（任意）

### 3.2 C: 学習/推論
- 学習: `train_jobs_count`, `train_success_rate`, `train_duration_min`, `eval_rmse/mae/mape`, `model_version`, `model_updated_at`
- 推論: `inference_latency_ms`（p50/p90/p99）, `inference_qps`, `feature_staleness_min`

### 3.3 D: 戦略実行
- KPI: `win_rate`, `max_drawdown`, `trade_count`, `avg_holding_time_min`, `pnl_realized`, `pnl_unrealized`
- 品質: `slippage_bps`, `order_fill_rate`, `order_reject_rate`, `latency_placement_ms`
- リスク: `risk_limit_breaches`, `circuit_breaker_triggers`

### 3.4 E: Plan層
- 取得: `collector_run_duration_sec`, `records_fetched`, `api_error_rate`, `data_lag_min`
- 特徴量: `feature_pipeline_duration_sec`, `missing_ratio`, `feature_drift_score`（要検討）
- 統計: `outlier_rate`, `schema_changes_detected`

---

## 4. 収集方式とデータフロー
- **a) アプリ内計測 → DB挿入**（FastAPIミドルウェア、学習/推論のフック、戦略実行ハンドラ等）
- **c) Airflow タスクからの集計**（DAG状態/ログ→集約テーブル）
- **d) ログETL**（戦略実行CSV/JSON・Airflowログを5分ごとに取り込み）

```mermaid
flowchart LR
  A[FastAPI ミドルウェア/例外] -->|a: INSERT| DB[(PostgreSQL)]
  C1[Train/Infer フック] -->|a: INSERT| DB
  D1[注文/約定/リスク処理] -->|a: INSERT| DB
  E1[collector/features/statistics] -->|a: INSERT| DB
  L[CSV/JSON/AFログ] -->|d: ETL 5分| ETL[Airflow ETL DAG] -->|c/d: UPSERT| DB
  DB --> HUD[/hud/observability]
```

---

## 5. 計測の仕込みポイント（確定）
### 5.1 A: FastAPI
- **ASGIミドルウェア（必須）**: リクエスト開始/終了・除外ルート（/static, /health）
- **例外ハンドラ（必須）**: 未捕捉例外/5xxの分類と計上
- **テンプレ描画計測（推奨）**: Jinja描画時間の追加記録

### 5.2 C: 学習/推論
- **学習ループ（必須）**: 各試行/エポック終了時 `loss/rmse/mae/経過秒/ステータス`
- **モデル保存直後（必須）**: `model_version/updated_at/評価指標`
- **推論入口/出口（必須）**: `latency_ms/success/feature_staleness_min`
- **特徴量変換完了（推奨）**: `pipeline_duration/rows/missing_ratio`

### 5.3 D: 戦略実行
- **注文発行前後（必須）**: 発行→約定までのレイテンシ、スリッページ
- **約定イベント（必須）**: 約定価格/数量/PNL/勝敗、リジェクト理由
- **リスクチェック前後（推奨）**: DDや上限超過、ブレーカー発動
- **日次・戦略単位集計（推奨）**: KPI集約をテーブル/ビューとして更新

### 5.4 E: Plan層
- **collector開始/終了（必須）**: 件数/時間/遅延/エラー率
- **features完了（必須）**: 所要時間/生成行数/欠損率
- **statistics完了（推奨）**: 集計時間/外れ値率/スキーマ変更
- **異常検知（推奨）**: 閾値越え時 `obs_alerts` に記録

---

## 6. アラート設計（採用）
- **A: FastAPI**  
  - p99レスポンス > **1500ms**（5分連続）  
  - 5xx率 > **2%**（10分平均）
- **C: 学習/推論**  
  - RMSE 前回比 > **+10%**  
  - 推論 p99 > **800ms**（5分連続）  
  - 特徴量鮮度 > **60分**
- **D: 戦略実行**  
  - MaxDD（30日ローリング） > **10%**  
  - Reject率 > **1%**（当日）  
  - 連敗数 ≥ **8**
- **E: Plan層**  
  - collector遅延 > **30分**  
  - 欠損率 > **5%**（重要列）

> **通知チャネル**: GUI内バナーのみ（Slack/Email等は**使わない**）

---

## 7. スキーマ（採用テーブル / 推奨DDL）
> **注意**: 実デプロイではプロジェクトの`core.path_config`に合わせたスキーマ名/インデックス名へ修正してください。

```sql
-- A: FastAPI
CREATE TABLE IF NOT EXISTS obs_api_requests (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  path TEXT NOT NULL,
  method TEXT NOT NULL,
  status INT NOT NULL,
  dur_ms INT NOT NULL,
  user_agent TEXT,
  err_flag BOOLEAN NOT NULL DEFAULT FALSE,
  template_render_ms INT
);
CREATE INDEX IF NOT EXISTS idx_obs_api_requests_ts ON obs_api_requests (ts);
CREATE INDEX IF NOT EXISTS idx_obs_api_requests_path ON obs_api_requests (path);

-- C: 学習ジョブ
CREATE TABLE IF NOT EXISTS obs_train_jobs (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  job_id TEXT,
  model TEXT,
  ver TEXT,
  status TEXT,       -- success/fail/interrupt
  dur_sec INT,
  rmse DOUBLE PRECISION,
  mae DOUBLE PRECISION,
  mape DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_obs_train_jobs_ts ON obs_train_jobs (ts);
CREATE INDEX IF NOT EXISTS idx_obs_train_jobs_model_ver ON obs_train_jobs (model, ver);

-- C: 推論
CREATE TABLE IF NOT EXISTS obs_infer_calls (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  model TEXT,
  ver TEXT,
  dur_ms INT,
  success BOOLEAN,
  feature_staleness_min INT
);
CREATE INDEX IF NOT EXISTS idx_obs_infer_calls_ts ON obs_infer_calls (ts);

-- D: 注文発行
CREATE TABLE IF NOT EXISTS obs_orders (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  strategy TEXT,
  type TEXT,         -- market/limit/...
  qty DOUBLE PRECISION,
  price DOUBLE PRECISION,
  lat_ms INT,
  filled BOOLEAN,
  rejected BOOLEAN,
  reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_obs_orders_ts ON obs_orders (ts);
CREATE INDEX IF NOT EXISTS idx_obs_orders_strategy ON obs_orders (strategy);

-- D: 約定
CREATE TABLE IF NOT EXISTS obs_trades (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  strategy TEXT,
  side TEXT,         -- buy/sell
  qty DOUBLE PRECISION,
  price DOUBLE PRECISION,
  pnl DOUBLE PRECISION,
  win_flag BOOLEAN,
  slippage_bps DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_obs_trades_ts ON obs_trades (ts);
CREATE INDEX IF NOT EXISTS idx_obs_trades_strategy ON obs_trades (strategy);

-- E: Plan層（collector/features/statistics）
CREATE TABLE IF NOT EXISTS obs_plan_runs (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  phase TEXT,              -- collector|features|statistics
  dur_sec INT,
  rows BIGINT,
  missing_ratio DOUBLE PRECISION,
  error_rate DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_obs_plan_runs_ts ON obs_plan_runs (ts);
CREATE INDEX IF NOT EXISTS idx_obs_plan_runs_phase ON obs_plan_runs (phase);

-- 共通: アラート
CREATE TABLE IF NOT EXISTS obs_alerts (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  severity TEXT,           -- Info/Warning/Critical
  source TEXT,             -- A|C|D|E
  key TEXT,                -- 例: p99_latency_ms
  value DOUBLE PRECISION,
  threshold DOUBLE PRECISION,
  message TEXT
);
CREATE INDEX IF NOT EXISTS idx_obs_alerts_ts ON obs_alerts (ts);
CREATE INDEX IF NOT EXISTS idx_obs_alerts_source ON obs_alerts (source);
```

---

## 8. データ保持とロールアップ（採用）
- **生データ**（`obs_api_requests`, `obs_orders`, `obs_trades`, `obs_infer_calls`, `obs_plan_runs`）  
  - **30日保持** → 以降は**日次集約**（平均/最大/分位など）にロールアップ
- **重要KPI**（`win_rate`, `max_drawdown`, `rmse`, `mae`, `mape`）  
  - **180日保持**
- **アラート**（`obs_alerts`）  
  - **90日保持**（Criticalは**180日**）

> 実装案: `*_daily` 集約テーブル（例: `obs_api_requests_daily`）＋Airflowの日次ロールアップDAG

---

## 9. HUD ルート `/hud/observability`
- **公開範囲**: **全員閲覧可（ログイン不要）**
- **レイアウト**: **要検討（保留）**  
  - 既存GUIにレイアウト/HTMLが生成済みのため、本ドキュメントでは拘束しない
- **バナー通知**: アラートはGUI内バナーで提示（外部通知なし）

---

## 10. 取り込み頻度と方式（採用）
- **頻度**: **5分ごと**
- **方式**: **Airflow のETL DAG**で集約実行  
  - 戦略実行ログ / Airflowログ → 5分ごとにETLし、UPSERTでDB更新  
  - FastAPI/学習・推論はアプリ側で**即時INSERT**（イベント駆動）

---

## 11. ランブック（運用手順・抜粋）
1. **初期化**
   - 本ドキュメントのDDLをPostgreSQLに適用
   - Airflowに「obs_etl_5min」「obs_rollup_daily」DAGを登録（要プロジェクト標準化）
2. **アプリ組み込み**
   - FastAPIミドルウェア/例外ハンドラ/テンプレ計測をON
   - 学習/推論/戦略実行/Plan層にフックを配置
3. **監視**
   - `/hud/observability` を常用
   - GUIバナーに重要アラートを露出
4. **保守**
   - 30日ごとにロールアップ結果のサイズ/性能確認
   - 閾値は四半期ごとに見直し（要検討）

---

## 12. 未決事項（要検討リスト）
- HUDの詳細レイアウト/画面分割、チャート構成、テーブルUI
- `feature_drift_score` の具体指標（PSI/KL/他）と閾値
- モデル/戦略ごとのタグ設計（モデル名・通貨ペア・期間など）
- 既存スキーマとの統合方針（スキーマ名、外部キーの付与）

---

## 13. 参考（実装スニペット / 任意）
> 実コードはプロジェクトに合わせて調整すること。

**FastAPI ミドルウェア概略**
```python
start = time.perf_counter()
try:
    resp = await call_next(request)
    err = resp.status_code >= 500
finally:
    dur_ms = int((time.perf_counter() - start) * 1000)
    if not request.url.path.startswith(("/static", "/health")):
        insert_obs_api_request(ts=now(), path=norm(request.url.path),
                               method=request.method, status=resp.status_code,
                               dur_ms=dur_ms, ua=request.headers.get("user-agent"),
                               err_flag=err, template_render_ms=getattr(request.state, "tpl_ms", None))
```

**学習ループ内ログ概略**
```python
log_train(job_id, model, ver, status="success", dur_sec=elapsed, rmse=rmse, mae=mae, mape=mape)
```

**推論入口/出口概略**
```python
t0 = now_ms()
y = model.predict(x)
lat_ms = now_ms() - t0
log_infer(model, ver, dur_ms=lat_ms, success=True, feature_staleness_min=stale_min)
```

**戦略実行（注文→約定）概略**
```python
log_order(strategy, type, qty, price, lat_ms, filled, rejected, reason)
log_trade(strategy, side, qty, price, pnl, win_flag, slippage_bps)
```

**Plan層フェーズ**
```python
log_plan_run(phase="collector", dur_sec=sec, rows=n, missing_ratio=mr, error_rate=er)
```

---

## 14. 変更履歴
- **2025-08-12**: 一問一答の決定を反映して全面更新。HUDレイアウトは保留。

