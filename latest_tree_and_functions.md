```plaintext

noctria_kingdom/
├── airflow_docker/                   # ⚙️ Airflow + Docker 統合運用環境
│   ├── dags/                         # DAG定義ファイル群（実行ワークフロー）
│   │   ├── noctria_kingdom_dag.py          # 王国全体統合DAG
│   │   ├── noctria_royal_dag.py            # 王単独の意思決定DAG
│   │   └── noctria_kingdom_pdca_dag.py     # Optuna → MetaAI → 戦略適用PDCA
│   ├── scripts/                      # DAGから実行される補助スクリプト
│   │   ├── optimize_params_with_optuna.py  # Optunaで戦略パラメータ最適化
│   │   ├── apply_best_params_to_metaai.py  # MetaAIへの反映
│   │   ├── apply_best_params.py            # Kingdom全体戦略への適用
│   │   └── run_veritas_generate_dag.py     # GUI経由でDAG起動用APIフック
│   ├── docker/                      # Dockerfile群（必要に応じて拡張）
│   │   └── Dockerfile
│   ├── airflow.cfg                 # Airflow設定ファイル
│   └── .env                        # 環境変数（APIキー等）※機密管理
│
├── core/                            # 🧠 中枢ロジック（王と共通処理）
│   ├── noctria.py                   # 王 Noctria の統合判断ロジック
│   ├── meta_ai.py                   # MetaAI（戦略統合・RL学習）
│   ├── logger.py                    # 共通ログユーティリティ
│   ├── reward.py                    # 独自報酬関数
│   └── risk_management.py           # リスク管理AI
│
├── strategies/                      # 🧠 戦略AI（四臣＋生成）
│   ├── aurus_singularis.py          # トレンド分析AI（Aurus）
│   ├── levia_tempest.py             # 短期価格判断AI（Levia）
│   ├── noctus_sentinella.py         # リスク監視AI（Noctus）
│   ├── prometheus_oracle.py         # ファンダ予測AI（Prometheus）
│   └── veritas_generator.py         # 自己進化AI Veritas（戦略生成）
│
├── envs/                            # 🧪 学習・検証用強化学習環境
│   ├── meta_ai_env_with_fundamentals.py    # ファンダ統合型RL環境
│   ├── meta_ai_env_with_sentiment.py       # センチメント対応型環境
│   └── meta_ai_env.py                       # MetaAI学習用汎用環境
│
├── institutions/                    # 🏦 制度的AIユニット（中央銀行など）
│   └── central_bank_ai.py           # 中央銀行ファンダAI
│
├── data/                            # 📊 CSV等の事前処理済みデータ
│   └── preprocessed_usdjpy_with_fundamental.csv
│
├── noctria_gui/                     # 🌐 GUI/外部連携
│   ├── backend/                     # FastAPIサーバ側
│   │   ├── main.py                  # エンドポイント定義
│   │   └── config.py                # 設定（ポート/APIキーなど）
│   └── frontend/                    # フロントエンド（任意）
│
├── README.md                        # 📝 プロジェクト概要と構成マップ
└── requirements.txt                 # Python依存パッケージ一覧
