# -------------------------------------------------------------------
# File: README_Act_Automation.md
# -------------------------------------------------------------------
# Noctria PDCA Act 自動化（運用メモ）

## 1. 事前準備
- Gitの環境変数を設定:
  - `GIT_REMOTE=origin`
  - `GIT_BRANCH=main`
  - （必要に応じて）`GIT_USER_NAME`, `GIT_USER_EMAIL`
- DB記録するなら:
  - `NOCTRIA_OBS_PG_DSN=postgresql://user:pass@host:5432/dbname`

## 2. 配置
- `airflow_docker/dags/noctria_act_pipeline.py`
- `src/pdca/selector.py`
- `src/pdca/apply_adoption.py`
- `src/core/git_utils.py`
- `src/core/decision_registry.py`
- `scripts/trigger_noctria_act.sh`（任意）

## 3. 実行
- AirflowでDAGが認識されていること:
  ```
  docker compose -f airflow_docker/docker-compose.yaml exec airflow-webserver airflow dags list | grep noctria_act_pipeline
  ```
- 手動トリガ例:
  ```
  bash scripts/trigger_noctria_act.sh \
    '{"LOOKBACK_DAYS":30,"WINRATE_MIN_DELTA_PCT":3,"MAX_DD_MAX_DELTA_PCT":2,"DRY_RUN":false,"TAG_PREFIX":"veritas","RELEASE_NOTES":"PDCA auto adopt"}'
  ```

## 4. 期待フロー
1) `collect_recheck_summary`: 直近ログから候補集計  
2) `decide_adoption`: 増分基準で採用可否判定  
3) `adopt_and_push`: 戦略ファイル生成→commit/push→tag  
4) `record_decision`: Decision Registryへ記録（DB or JSONL）

## 5. 注意
- ログ・再評価フォーマットは `selector.py` の期待キーに合わせるか、必要に応じて調整
- 実戦略コード生成は `apply_adoption._render_strategy_stub` をテンプレートベースに差し替え推奨
- 競合時は `git pull --rebase` を挟んでPush（簡易実装済み）
