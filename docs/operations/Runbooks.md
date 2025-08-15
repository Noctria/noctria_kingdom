# 🧭 Runbooks — Noctria Kingdom Operations

**Version:** 1.1  
**Status:** Adopted (pending PR merge)  
**Last Updated:** 2025-08-14 (JST)

> 目的：本番/検証環境での **日次運用・障害対応・変更適用** を、誰が読んでも同じ品質で実行できるようにする。  
> 関連：`../governance/Vision-Governance.md` / `../architecture/Architecture-Overview.md` / `../observability/Observability.md` / `./Airflow-DAGs.md` / `./Config-Registry.md` / `../security/Security-And-Access.md`

---

## 1. 対象範囲と前提
- **対象**：Airflow（DAG 実行）、GUI（FastAPI）、戦略実行（Do 層）、学習/評価（Plan/Check/Act）の日次運用と障害対応  
- **環境**：`prod` / `stg` / `dev`（本書のコマンドは代表例）  
- **前提**
  - アクセス権限は `Security-And-Access.md` に準拠（最小権限＋監査ログ）
  - 設定変更は `Config-Registry.md` と **ENV** を正とする（Git へ秘密を置かない）
  - 重要判断は `Vision-Governance.md` の **RACI / ガードレール**に従う

---

## 2. サマリ（運用フロー）

```mermaid
flowchart LR
  A[Start of Day] --> H[Health Checks]
  H --> D[Airflow Jobs]
  D --> T[Trading Window]
  T --> C[Close & KPIs]
  C --> R[Review & Hand-off]
  R -->|incidents?| I[Incident Playbooks]
```

---

## 3. 日次運用チェックリスト（SoD / EoD）

### 3.1 Start of Day（SoD, 市場前）
- [ ] **Airflow** `scheduler/webserver/worker` が健全（WebUI `/health` 200）
- [ ] **GUI** `/healthz` が 200（既定ポート **8001**）
- [ ] **PostgreSQL** 到達性と残容量（`df -h`, `pg_isready`）
- [ ] 機密（API キー/トークン/証明書）期限の警告なし
- [ ] 前営業日の `exec_result` / `risk_event` 取り込み済み（ETL 成功）
- [ ] **取引抑制フラグ**（`risk_policy.global_trading_pause`）=`false` を確認（本番）

### 3.2 End of Day（EoD, 市場後）
- [ ] `pdca_check_flow` 完走（KPI 生成）→ GUI 反映
- [ ] `pdca_summary` 生成済み
- [ ] 失敗 DAG の手動再実行は **3 回まで**（超過でインシデント起票）
- [ ] バックアップ/スナップショット完了
- [ ] 翌営業日のイベント/祝日設定を確認（`Config-Registry`）

---

## 4. スタック起動/停止（標準手順）

### 4.1 GUI（FastAPI, Gunicorn, systemd 管理）
**ユニット**：`/etc/systemd/system/noctria_gui.service`  
**環境ファイル**：`/etc/default/noctria-gui`（LF, 644, root:root）

```bash
# 起動/停止/再起動/状態
sudo systemctl start  noctria_gui
sudo systemctl stop   noctria_gui
sudo systemctl restart noctria_gui
sudo systemctl status  noctria_gui --no-pager

# 直近ログ
sudo journalctl -u noctria_gui -n 200 --no-pager

# 環境が正しく入っているか（ENV/ExecStart/EnvironmentFiles）
sudo systemctl show -p Environment -p ExecStart -p EnvironmentFiles noctria_gui

# ポート 8001 で待受しているか
ss -ltnp | grep ':8001' || sudo journalctl -u noctria_gui -n 80 --no-pager

# 健全性
curl -sS http://127.0.0.1:8001/healthz
```

> **ENV 例（/etc/default/noctria-gui）**
> ```
> NOCTRIA_OBS_PG_DSN=postgresql://noctria:noctria@127.0.0.1:55432/noctria_db
> NOCTRIA_GUI_PORT=8001
> ```

**重要ノート**
- 環境変数展開のため、`ExecStart` は **`/bin/sh -lc 'exec ... --bind 0.0.0.0:${NOCTRIA_GUI_PORT:-8001} ...'`** で起動する（sh 経由で展開）。  
- **CRLF 混入**で環境が読まれないことがある。疑わしい場合：
  ```bash
  sudo sed -n 'l' /etc/default/noctria-gui   # 行末に ^M があれば CRLF
  sudo apt-get update && sudo apt-get install -y dos2unix
  sudo dos2unix /etc/default/noctria-gui
  sudo chown root:root /etc/default/noctria-gui && sudo chmod 644 /etc/default/noctria-gui
  sudo systemctl daemon-reload && sudo systemctl restart noctria_gui
  ```

### 4.2 Airflow（Docker Compose 管理の例）
```bash
# 起動
docker compose -f deploy/prod/docker-compose.yml up -d airflow-scheduler airflow-webserver airflow-worker

# 計画停止
docker compose -f deploy/prod/docker-compose.yml stop airflow-worker airflow-webserver airflow-scheduler

# ログ
docker compose -f deploy/prod/docker-compose.yml logs -f airflow-scheduler
```

---

## 5. Airflow 運用（DAG 操作の定石）
- 原則 **idempotent**（副作用ありは Runbook に明記）
- 失敗時の自動リトライ回数と手動再実行手順を統一

```bash
# DAG 有効/無効
airflow dags pause  train_prometheus_obs8
airflow dags unpause pdca_check_flow

# バックフィル（UTC 基準）
airflow dags backfill -s 2025-08-01 -e 2025-08-12 pdca_check_flow

# 失敗タスクのクリア（依存含む）
airflow tasks clear -t <task_id> -s 2025-08-12 -e 2025-08-12 -y pdca_check_flow

# 健全性（WebUI 側）
curl -s http://localhost:8080/health
```

---

## 6. 可観測性（Observability）運用手順
- **GUI ルート**
  - `GET /pdca/timeline`：トレース時系列（Plan/Infer/Decision/Exec/Alert）
  - `GET /pdca/latency/daily`：日次レイテンシ（p50/p90/p95/max, traces）
  - `POST /pdca/observability/refresh`：ビュー/マテビューの確保・更新
- **DB ビュー/MVIEW**
  - `obs_trace_timeline` / `obs_trace_latency` / `obs_latency_daily`（詳細は `../observability/Observability.md`）
- **手動リフレッシュ**
  ```bash
  # GUI 経由
  curl -X POST -sS http://127.0.0.1:8001/pdca/observability/refresh

  # 直接 SQL
  psql "$NOCTRIA_OBS_PG_DSN" -c 'REFRESH MATERIALIZED VIEW obs_latency_daily;'
  ```
- **保持方針**
  - 原始イベントは 30 日保持 → 日次ロールアップ参照（運用で適宜 VACUUM/パーティション）

---

## 7. 取引の一時停止/再開（グローバル抑制）
**目的**：異常検知・市場急変時に **全戦略発注を即時停止**。

```bash
# 抑制フラグ ON
./ops/tools/toggle_trading_pause.sh --env prod --on

# 再開
./ops/tools/toggle_trading_pause.sh --env prod --off
```

- 反映先：`Config-Registry.md` の `risk_policy.global_trading_pause`  
- GUI（権限制御下）から `/ops/pause` でも切り替え可

---

## 8. 新規戦略の本番導入（Deploy/Adopt）
**前提**：`Strategy-Lifecycle.md` 承認、`Noctus` リスク審査 OK、`Hermes` 説明文あり。

1. **stg** で 3 営業日 A/B 検証（`pdca_recheck.py` → KPI 比較）  
2. King 承認後、本番に **低ロット** で段階導入（7% → 30% → 100%）  
3. `pdca_push.py` で採用反映 → `Release-Notes.md` 更新  
4. 導入後 24h は **強化監視**（閾値 0.5x）  
5. 重大異常は §7 の抑制で即停止 → インシデントへ

---

## 9. ロールバック（段階的復帰）
- 即時停止：§7 の抑制フラグ ON  
- 段階ロールバック：
  1) 最新戦略を無効化 → 直前安定版へ切替  
  2) 影響データを除外フラグでマーキング  
  3) KPI 再集計（`pdca_check_flow`）で回復確認  
- 完了後 `Incident-Postmortems.md` に復旧記録

---

## 10. 障害対応プレイブック

### 10.1 GUI が起動しない / ポート未待受
**症状**：`curl /healthz` が失敗、`ss -ltnp | grep :8001` で LISTEN なし  
**確認/対処**
1. `sudo systemctl status noctria_gui` / `journalctl -u noctria_gui -n 200`  
2. ログに **`'$NOCTRIA_GUI_PORT' is not a valid port number`** → `ExecStart` が **sh 経由**か確認  
   - `systemctl show -p ExecStart noctria_gui` に **`/bin/sh -lc`** が含まれること  
3. `EnvironmentFiles=/etc/default/noctria-gui` が読まれているか  
   - `systemctl show -p Environment -p EnvironmentFiles noctria_gui`  
   - ENV に `NOCTRIA_GUI_PORT=8001` と `NOCTRIA_OBS_PG_DSN=...` が出ること  
4. CRLF 疑い → §4.1 の `dos2unix` を実施  
5. 競合プロセス → `ss -ltnp | grep ':8001'` で既存プロセスを特定し解放  
6. 再起動 → `systemctl daemon-reload && systemctl restart noctria_gui`

### 10.2 `/pdca/*` が 500（DB 認証/接続失敗）
**症状**：GUI ログに `psycopg2.OperationalError: FATAL:  password authentication failed for user "noctria"`  
**確認/対処**
1. ENV の DSN を確認：`cat /etc/default/noctria-gui`  
   - 例：`postgresql://noctria:noctria@127.0.0.1:55432/noctria_db`（**Docker の 5432→WSL では 55432 に NAT** されている例）  
2. DB 到達性：`pg_isready -h 127.0.0.1 -p 55432 -d noctria_db -U noctria`  
3. パスワード再設定（必要時）：`psql -h 127.0.0.1 -p 55432 -U postgres -c "ALTER USER noctria WITH PASSWORD 'noctria';"`  
4. 反映：`systemctl restart noctria_gui`

### 10.3 可観測ビューが空/欠損
**症状**：タイムライン/レイテンシが空  
**対処**
1. GUI から `POST /pdca/observability/refresh` を叩く  
2. 直接 SQL：`REFRESH MATERIALIZED VIEW obs_latency_daily;`  
3. ETL ログを確認（Airflow ETL DAG の失敗/遅延）

### 10.4 Airflow スケジューラ停止
**症状**：DAG が走らない、WebUI に `scheduler down`  
**対処**
1. コンテナログ：`docker compose ... logs -f airflow-scheduler`  
2. DB/ブローカー死活：`pg_isready` / メッセージブローカー確認  
3. `airflow db check` → 失敗時は `airflow db migrate` 後に再起動  
4. 復旧後、該当期間をバックフィル（§5）

### 10.5 発注遅延/約定異常（Do 層）
**症状**：`exec_result` 遅延/異常値  
**対処**
1. `broker_adapter` ログ疎通  
2. スリッページ閾値超過は自動停止トリガ → §7 で即停止  
3. 連敗閾値超過 → `risk_event` → 抑制 ON + インシデント

---

## 11. バックアップ & リストア
- **対象**：`pdca_logs/**/*.json`、戦略リリースメタ、学習済みモデル（`/models/**`）、設定（`Config-Registry`）
- **頻度**：日次（EoD）、重要 DAG 実行後はスナップショット  
- **リストア概略**
  1) 対象日のスナップショットをマウント  
  2) 必要時 `exec_result` を監査ログから再構成  
  3) `pdca_check_flow` をバックフィル実行

---

## 12. 機密/アクセス（運用観点）
- **Secrets** は ENV/Vault のみ（平文ファイル禁止）  
- アクセスは **最小権限**＋**監査ログ有効化**  
- 運用者権限変更は申請フロー必須（`Security-And-Access.md`）

---

## 13. メンテナンスウィンドウ
- **火曜 02:00–03:00 JST（prod）**：OS/ライブラリ/DB メンテ  
- 影響：取引停止→GUI バナー→完了後に健全性チェック（SoD の簡易版）

---

## 14. 変更管理（Runbook 反映）
- 重要変更は **同一 PR で Runbooks を更新**  
- 承認フローは `Vision-Governance.md` の **RACI** に従う  
- Merge 後に `Release-Notes.md` / `CHANGELOG` を更新

---

## 15. テンプレ & ショートカット

### 15.1 手順テンプレ
```md
## {手順名}
- 目的:
- 前提:
- 手順:
- ロールバック:
- 検証/完了条件:
- 監査ログ/保存先:
```

### 15.2 よく使うコマンド
```bash
# Airflow 健全性
curl -s http://localhost:8080/health

# 直近失敗タスク一覧
airflow tasks list pdca_check_flow --tree
airflow tasks failed --since 1d

# GUI 健全性（port は ENV を反映）
curl -sS http://127.0.0.1:${NOCTRIA_GUI_PORT:-8001}/healthz
```

### 15.3 連絡・エスカレーション
| 種別 | 連絡先 | 役割 |
|---|---|---|
| On-call Ops | #ops-oncall | 一次対応 |
| Risk Duty (Noctus) | #risk-duty | リスク判断 |
| Council | #council | 重要決定 |
| King | #king | 最終承認 |

---

## 16. 既知の課題（Known Issues）
- Airflow バックフィルの高 I/O → ストレージ IOPS 制限に注意  
- 一部ブローカーのテスト環境でレート制限が厳格 → 夜間にまとめて検証  
- GUI の **ENV 読み込み**は改行/引用符/空白に敏感（`/etc/default/noctria-gui` を常に LF・2 行・無駄な引用/空白なしに保つ）

---

## 17. 変更履歴（Changelog）
- **2025-08-14**: v1.1
  - GUI 運用を **systemd 標準**へ更新（`/etc/default/noctria-gui` / ポート 8001 / `sh -lc` 展開）
  - Observability の **/pdca/timeline** / **/pdca/latency/daily** / **refresh** 手順を追加
  - インシデントに **DB 認証失敗** / **ENV 展開不備** / **CRLF** を追加
- **2025-08-12**: v1.0 初版

<!-- AUTOGEN:CHANGELOG START -->

### 🛠 Updates since: `2025-08-13 17:50 UTC`

- `4715c7b` 2025-08-15T05:12:32+09:00 — **Update update_docs_from_index.py** _(by Noctoria)_
  - `scripts/update_docs_from_index.py`
- `c20a9bd` 2025-08-15T04:58:31+09:00 — **Create update_docs_from_index.py** _(by Noctoria)_
  - `scripts/update_docs_from_index.py`
- `969f987` 2025-08-15T04:36:32+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `a39c7db` 2025-08-15T04:14:15+09:00 — **Update observability.py** _(by Noctoria)_
  - `src/plan_data/observability.py`
- `09a3e13` 2025-08-15T03:51:14+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `aea152c` 2025-08-15T03:34:12+09:00 — **Update strategy_detail.py** _(by Noctoria)_
  - `noctria_gui/routes/strategy_detail.py`
- `3bc997c` 2025-08-15T03:23:40+09:00 — **Update strategy_detail.py** _(by Noctoria)_
  - `noctria_gui/routes/strategy_detail.py`
- `482da8a` 2025-08-15T03:02:26+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `feef06f` 2025-08-15T02:33:44+09:00 — **Update docker-compose.yaml** _(by Noctoria)_
  - `airflow_docker/docker-compose.yaml`
- `e4e3005` 2025-08-15T02:15:13+09:00 — **Update __init__.py** _(by Noctoria)_
  - `noctria_gui/__init__.py`
- `4b38d3b` 2025-08-15T01:48:52+09:00 — **Update path_config.py** _(by Noctoria)_
  - `src/core/path_config.py`
- `00fc537` 2025-08-15T01:44:12+09:00 — **Create kpi_minidemo.py** _(by Noctoria)_
  - `src/plan_data/kpi_minidemo.py`
- `daa5865` 2025-08-15T01:37:54+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `5e52eca` 2025-08-15T01:35:28+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `e320246` 2025-08-15T01:34:39+09:00 — **Update Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `de39f94` 2025-08-15T01:33:29+09:00 — **Create Aurus_Singularis.py** _(by Noctoria)_
  - `src/strategies/veritas_generated/Aurus_Singularis.py`
- `e4c82d5` 2025-08-15T01:16:27+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `47a5847` 2025-08-15T01:06:11+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `15188ea` 2025-08-15T00:59:08+09:00 — **Update __init__.py** _(by Noctoria)_
  - `noctria_gui/__init__.py`
- `1b4c2ec` 2025-08-15T00:41:34+09:00 — **Create statistics_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/statistics_routes.py`
- `49795a6` 2025-08-15T00:34:44+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `4d7dd70` 2025-08-15T00:28:18+09:00 — **Update act_service.py** _(by Noctoria)_
  - `src/core/act_service.py`
- `1d38c3c` 2025-08-14T22:21:33+09:00 — **Create policy_engine.py** _(by Noctoria)_
  - `src/core/policy_engine.py`
- `dcdd7f4` 2025-08-14T22:15:59+09:00 — **Update airflow_client.py** _(by Noctoria)_
  - `src/core/airflow_client.py`
- `e66ac97` 2025-08-14T22:08:25+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `6c49b8e` 2025-08-14T21:58:17+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `e0b9eaa` 2025-08-14T21:53:00+09:00 — **Update pdca_summary_service.py** _(by Noctoria)_
  - `src/plan_data/pdca_summary_service.py`
- `368203e` 2025-08-14T21:44:48+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `cc9da23` 2025-08-14T21:32:42+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `434d2e2` 2025-08-14T21:23:55+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `d0df823` 2025-08-14T21:18:54+09:00 — **Update decision_registry.py** _(by Noctoria)_
  - `src/core/decision_registry.py`
- `1eaed26` 2025-08-14T21:08:01+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `b557920` 2025-08-14T21:03:59+09:00 — **Update strategy_evaluator.py** _(by Noctoria)_
  - `src/core/strategy_evaluator.py`
- `0c7a12f` 2025-08-14T21:00:00+09:00 — **Create decision_registry.py** _(by Noctoria)_
  - `src/core/decision_registry.py`
- `2f034a5` 2025-08-14T20:58:16+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `28bb890` 2025-08-14T20:51:37+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `307da2d` 2025-08-14T20:49:15+09:00 — **Create act_service.py** _(by Noctoria)_
  - `src/core/act_service.py`
- `bf993f3` 2025-08-14T20:41:12+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `4b7ca22` 2025-08-14T20:35:18+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `3880c7b` 2025-08-14T20:32:42+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `074b6cf` 2025-08-14T20:24:03+09:00 — **Update pdca_routes.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `46d639d` 2025-08-14T20:17:49+09:00 — **Update strategy_evaluator.py** _(by Noctoria)_
  - `src/core/strategy_evaluator.py`
- `f63e897` 2025-08-14T20:12:50+09:00 — **Update veritas_recheck_dag.py** _(by Noctoria)_
  - `airflow_docker/dags/veritas_recheck_dag.py`
- `7c3785e` 2025-08-14T20:08:26+09:00 — **Create veritas_recheck_all_dag.py** _(by Noctoria)_
  - `airflow_docker/dags/veritas_recheck_all_dag.py`
- `49fe520` 2025-08-14T15:41:00+09:00 — **main.py を更新** _(by Noctoria)_
  - `noctria_gui/main.py`
- `3648612` 2025-08-14T15:35:27+09:00 — **pdca_routes.py を更新** _(by Noctoria)_
  - `noctria_gui/routes/pdca_routes.py`
- `f7f1972` 2025-08-14T06:32:19+09:00 — **Update base_hud.html** _(by Noctoria)_
  - `noctria_gui/templates/base_hud.html`
- `eae18c6` 2025-08-14T06:21:35+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `1d6047c` 2025-08-14T06:10:33+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `3c55ed0` 2025-08-14T06:04:20+09:00 — **Create dammy** _(by Noctoria)_
  - `noctria_gui/static/vendor/dammy`
- `7b4624d` 2025-08-14T05:45:03+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `35e4c50` 2025-08-14T04:49:16+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `6c88b9f` 2025-08-14T04:31:58+09:00 — **Update pdca_summary.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_summary.html`
- `1a0b00e` 2025-08-14T04:29:17+09:00 — **Update pdca_summary.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_summary.py`
- `2b51ef9` 2025-08-14T04:27:11+09:00 — **Create pdca_summary_service.py** _(by Noctoria)_
  - `src/plan_data/pdca_summary_service.py`
- `6ff093a` 2025-08-14T04:24:34+09:00 — **Update main.py** _(by Noctoria)_
  - `noctria_gui/main.py`
- `7e2e056` 2025-08-14T04:20:51+09:00 — **Create pdca_control.html** _(by Noctoria)_
  - `noctria_gui/templates/pdca_control.html`
- `cf248ee` 2025-08-14T04:15:18+09:00 — **Update pdca_recheck.py** _(by Noctoria)_
  - `noctria_gui/routes/pdca_recheck.py`
- `d8e0d6e` 2025-08-14T04:12:02+09:00 — **Create airflow_client.py** _(by Noctoria)_
  - `src/core/airflow_client.py`

<!-- AUTOGEN:CHANGELOG END -->
<!-- AUTODOC:BEGIN mode=git_log path_globs="docs/operations/*.md;docs/misc/*.md" title=運用ドキュメント更新履歴（最近30） limit=30 since=2025-08-01 -->
### 運用ドキュメント更新履歴（最近30）

- **30ae379** 2025-08-15T18:55:06+09:00 — 📄 AutoDoc: update docs from index (by Veritas Machina)
  - `action`
  - `data/decisions/ledger.csv`
  - `data/models/prometheus/PPO/obs8/latest`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:18:10+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:18:10+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:19:41+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:19:41+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:22:19+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:22:19+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:33:11+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:33:11+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T15:44:05+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T15:44:05+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:20:12.935706+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:20:12.935706+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:21:36.023694+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:21:36.023694+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:27:02.701382+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:27:02.701382+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T17:21:59.539332+00:00/metadata.json`
- **d09c7ae** 2025-08-15T05:31:20+09:00 — docs: update from 00-INDEX.md sync (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/_generated/update_docs.log`
  - `docs/adrs/ADRs.md`
  - `docs/apis/API.md`
  - `docs/apis/Do-Layer-Contract.md`
  - `docs/apis/observability/Observability.md`
  - `docs/architecture/Architecture-Overview.md`
  - `docs/architecture/Plan-Layer.md`
  - `docs/governance/Coding-Standards.md`
  - `docs/governance/Vision-Governance.md`
  - `docs/incidents/Incident-Postmortems.md`
  - `docs/models/ModelCard-Prometheus-PPO.md`
  - `docs/models/Strategy-Lifecycle.md`
  - `docs/observability/Observability.md`
  - `docs/operations/Airflow-DAGs.md`
  - `docs/operations/Config-Registry.md`
  - `docs/operations/Runbooks.md`
  - `docs/qa/Testing-And-QA.md`
  - `docs/risks/Risk-Register.md`
  - `docs/roadmap/Release-Notes.md`
- **02b8516** 2025-08-14T02:56:00+09:00 — Update Config-Registry.md (by Noctoria)
  - `docs/operations/Config-Registry.md`
- **1a4b22e** 2025-08-14T02:50:27+09:00 — Update Runbooks.md (by Noctoria)
  - `docs/operations/Runbooks.md`
- **3373062** 2025-08-12T10:56:04+09:00 — Airflow-DAGs.md を更新 (by Noctoria)
  - `docs/operations/Airflow-DAGs.md`
- **3998941** 2025-08-12T04:39:48+09:00 — Update Config-Registry.md (by Noctoria)
  - `docs/operations/Config-Registry.md`
- **05d3f5d** 2025-08-12T04:36:19+09:00 — Update Runbooks.md (by Noctoria)
  - `docs/operations/Runbooks.md`
- **a410532** 2025-08-12T03:01:21+09:00 — Create Airflow-DAGs.md (by Noctoria)
  - `docs/operations/Airflow-DAGs.md`
- **9371b3c** 2025-08-12T03:01:04+09:00 — Create Config-Registry.md (by Noctoria)
  - `docs/operations/Config-Registry.md`
- **ee7cb52** 2025-08-12T03:00:26+09:00 — Create Runbooks.md (by Noctoria)
  - `docs/operations/Runbooks.md`
<!-- AUTODOC:END -->
