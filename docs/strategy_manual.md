<!-- AUTODOC:BEGIN mode=file_content path_globs=/mnt/d/noctria_kingdom/docs/_partials_full/docs/strategy_manual.md -->
# 🤖 Noctria Kingdom 戦略AI説明

## AurusSingularis
- 市場トレンドをLSTMなどで分析
- 入力: 1h場のヒストリカルデータ
- 出力: BUY / SELL / HOLD
- ログ: `/opt/airflow/logs/AurusLogger.log`

## LeviaTempest
- RSI, ブレイクアウトなど短期ロジックに特化
- スプレッドや時間帯条件も加味
- ログ: `/opt/airflow/logs/LeviaLogger.log`

## NoctusSentinella
- ボラティリティ・スプレッド・スリッページからリスク判定
- 高リスク環境下でのトレード制限
- ログ: `/opt/airflow/logs/NoctusLogger.log`

## PrometheusOracle
- CPI, GDP, 失業率などのマクロ指標を評価
- ファンダメンタルスコアに応じた方向性判断
- ログ: `/opt/airflow/logs/PrometheusLogger.log`

## Noctria（統合判断AI）
- 各AIの出力をXCom経由で受け取り
- シグナル重み付き合算またはルールベースで統合判断
- ログ: `/opt/airflow/logs/system.log`
<!-- AUTODOC:END -->
