noctria-kingdom/
├── airflow-docker/              # Airflow本体（Docker運用環境）
│   ├── dags/                    # DAG定義ファイル群
│   ├── core/                    # Airflowから参照する戦略・ユーティリティ
│   ├── data/                    # airflowが扱うデータ
│   ├── docker/                  # Dockerfile, requirements
│   ├── logs/                    # Airflowログ（マウント先）
│   ├── plugins/                 # 必要ならカスタムプラグイン
│   ├── scripts/                 # メタAIなど実行スクリプト
│   ├── strategies/             # 各AI戦略（Airflow用）
│   └── docker-compose.yaml
│
├── noctria-core/                # Airflow外で動く学習・推論・EA群
│   ├── core/                    # 共通AIユーティリティ
│   ├── data/                    # 高頻度データ + ファンダメンタルなど
│   ├── strategies/             # EAやAI戦略の中核
│   ├── execution/              # 実行系（トレード、API連携）
│   ├── optimization/           # Optunaなどの最適化コード
│   ├── experts/                # MQL5のEAソース群
│   ├── models/                 # 学習済みモデルの保存
│   └── tests/                  # unittest + integration test
│
├── docs/                        # 技術ドキュメント・戦略解説
│   ├── README.md
│   └── strategy_manual.md
│
├── gui/                         # Noctria-GUI（分離して統合）
│   ├── frontend/
│   └── backend/
│
├── tools/                       # スクリプトや分析ツールなど
│   ├── meta_ai_tensorboard_train.py
│   ├── analyze_results.py
│   └── ...
│
├── .secrets/                    # APIキーやkubeconfigなど（gitignore対象）
│   └── kubeconfig_final.yaml
│
├── .gitignore
└── README.md
