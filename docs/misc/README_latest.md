| カテゴリ                   | ディレクトリ                                | 主な内容・目的                                       |
| ---------------------- | ------------------------------------- | --------------------------------------------- |
| 🧠 **統合AI（王 Noctria）** | `core/noctria.py`                     | 四臣の判断を統合し、最終トレード判断を行う中枢AI                     |
| 📊 **戦略AI（四臣）**        | `strategies/`                         | 各専門領域のAIモジュール（トレンド、スキャル、リスク、ファンダ）             |
| 🤖 **自己進化AI（Veritas）** | `strategies/veritas_generator.py`     | 強化学習や生成AIを活用して戦略構造を自動生成・評価する統合戦略生成AI          |
| 🏋️ **学習・評価環境**        | `envs/`                               | PPO強化学習用のトレーディング環境。センチメント・ファンダメンタル情報も統合可能     |
| 📦 **戦略最適化スクリプト**      | `airflow_docker/scripts/`             | Optuna最適化・MetaAI適用・GUI起動・XCom変換用スクリプト群        |
| 🔁 **Airflow DAG群**    | `airflow_docker/dags/`                | トレード戦略実行・PDCA最適化・MetaAI学習などのAirflowタスク群       |
| 🗃 **共通ユーティリティ**       | `core/logger.py`, `reward.py`         | ログ出力、報酬関数、センチメント取得などの共通ロジック                   |
| 🏦 **制度的AIユニット**       | `institutions/central_bank_ai.py`     | 中央銀行を模したファンダ判断AIユニット（利上げ／インフレ環境の影響を評価）        |
| 📁 **データ格納先**          | `data/`                               | トレーニング・実行用の事前処理済みデータCSV格納先                    |
| 🌐 **GUI/API連携**       | `scripts/run_veritas_generate_dag.py` | FastAPI経由でDAGを起動し、外部アプリと統合（フロント表示用のログJSON化含む） |
