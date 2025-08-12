# Airflow 環境プロファイル（Noctria固有・記入テンプレ）

## 1) インフラ / デプロイ
- デプロイ形態: （例）Docker Compose / K8s / MWAA / Astronomer
- Airflow バージョン: （例）2.8.3
- Executor: （例）Celery / Local / Kubernetes
- ワーカー: （例）3台 / autoscalingなし
- メタDB: （例）PostgreSQL 14 / 専用RDS
- メッセージブローカー: （例）Redis 6 / RabbitMQ 3.12
- デプロイ窓口: （例）GitHub Actions → Docker Registry → 本番ノード pull

## 2) 環境（dev/stg/prod）差分
- スケジュール差分: （例）stgはcron半分、prodは平日営業日のみ
- 並列度差分: （例）dev:1 / stg:2 / prod:5
- Flags差分: （例）prodのみ `risk_safemode: true`
- タイムゾーン運用: Airflow=UTC / 表示=JST（Yes/No）

## 3) 取引カレンダー / 営業時間（JST）
- マーケット/銘柄範囲: （例）現物USDTペア（BTC/USDT, ETH/USDT）
- 取引ウィンドウ（JST）: （例）24/5 ただし 5分足で実行
- 休場カレンダー: （例）Cryptoは常時、FX/株は `jp-holidays` 使用
- 祝日対応方針: （例）DAGは走るがDo層はドライラン 等

## 4) DAG在庫（正式ID・Owner・SLA）
- `pdca_plan_workflow`: owner=ops, schedule= `0 5 * * 1-5` (UTC), SLA=30m
- `do_layer_flow`: owner=ops, schedule= `*/5 0-23 * * 1-5`, SLA=5m, critical=true
- `pdca_check_flow`: owner=risk, schedule=`15 16 * * 1-5`, SLA=20m
- `pdca_act_flow`: owner=ops, schedule=`0 17 * * 1-5`, SLA=45m
- `train_prometheus_obs8`: owner=models, schedule=`0 3 * * 6`, SLA=2h
- `oracle_prometheus_infer_dag`: owner=models, schedule=`0 6 * * 1-5`, SLA=20m
- その他: （あれば列挙）

## 5) Queues / Pools / Concurrency
- Celery/K8s Queue: （例）`default`, `critical_do`, `models`
- Pool: （例）`broker_pool(size=5)`, `gpu_pool(size=1)`
- `max_active_runs_per_dag`: （例）`do_layer_flow=3` 他は1
- `max_active_tasks_per_dag`: （例）共通10
- 重たいタスク: （例）学習系は `models` キューで隔離

## 6) Variables / Connections（実名）
- Variables:
  - `env`: dev|stg|prod
  - `risk_policy`: （JSON 例を貼る）
  - `flags`: （JSON 例を貼る）
  - `dag_defaults`: （retries, retry_delay, sla 等）
- Connections:
  - `broker_http`（Do層の外部ブローカーAPI）
  - `db_primary`（実績集計DB）
  - `slack_webhook`（通知）
  - 追加があれば…

## 7) データI/Oパス（実パス）
- 入力: `/data/market/**`, `/data/execution_logs/*.json`
- 出力: `/data/pdca_logs/kpi_summary.json`, `/data/audit/*.json`
- モデル: `/models/prometheus/**`
- 共有ボリューム: （例）`/mnt/noctria-shared`（NFS/EFS）

## 8) リトライ / SLA / 失敗時方針
- デフォルト retries: （例）2 / delay 5m / backoff: exp
- 重要DAG（do_layer_flow）: retries=4, SLA miss → PagerDuty
- SLAミス通知: Slack の #ops-alerts / PagerDuty Sev2
- 3回以上連続失敗したら: `flags.global_trading_pause=true`（Yes/No）

## 9) バックフィル / 再実行ルール
- 実行許可時間帯: （例）JST 01:00–05:00 のみ
- 影響の大きいDAG: （例）do_layer_flow は原則バックフィル禁止
- 手順: Runbooks §12 準拠（要リンク）

## 10) 監視 / 通知
- メトリクス: Prometheus（port, scrape間隔）
- ダッシュボード: GrafanaダッシュボードURL（任意）
- アラート送信先: Slack `#ops-alerts`, `#risk-duty`, PagerDutyサービス名
- 可観測ログ: Loki/ELK 等（あれば）

## 11) セキュリティ / 守るべきルール
- Secrets Backend: （例）HashiCorp Vault / AWS Secrets Manager
- 実行権限: Airflowサービスアカウント（ロール名）
- 操作ログ: Web UI 操作は監査に保存（Yes/No）
- 禁止事項: （例）Variables に秘密を入れない、`risk_policy` 越境は禁止項目

## 12) 既知の制約 / スループット
- 1分あたりの平均注文数: （例）5〜20
- 市場ピーク時のタスク完了遅延: （例）最大2分
- ボトルネック: （例）I/O / ブローカーAPI レート制限 / GPU枯渇

## 13) ドキュメント紐づけ
- Runbooks: `docs/operations/Runbooks.md`（Yes/No）
- Config: `docs/operations/Config-Registry.md`（Yes/No）
- Observability: `docs/observability/Observability.md`（Yes/No）
- Security: `docs/security/Security-And-Access.md`（Yes/No）
- ADR: `docs/adrs/`（必要時に追記）


