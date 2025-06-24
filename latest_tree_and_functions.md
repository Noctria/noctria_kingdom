noctria_kingdom/
├── airflow_docker/
│   ├── dags/
│   │   ├── strategies/               # 各AI戦略を呼び出すDAG
│   │   │   ├── aurus_strategy_dag.py
│   │   │   ├── levia_strategy_dag.py
│   │   │   ├── prometheus_strategy_dag.py
│   │   │   └── noctus_strategy_dag.py
│   │   ├── integration/             # 複数戦略統合（XCom, Noctria統合など）
│   │   │   ├── noctria_kingdom_dag.py       # 王Noctriaによる統合判断
│   │   │   ├── noctria_royal_dag.py         # 王の最終判断のみ
│   │   │   └── veritas_master_dag.py        # Veritasによる戦略生成統括
│   │   ├── training/
│   │   │   ├── metaai_train_dag.py          # MetaAI強化学習用
│   │   │   └── metaai_evaluate_dag.py       # 学習済みAIの評価用
│   │   └── pdca/
│   │       └── noctria_kingdom_pdca_dag.py  # Optuna最適化 → 再学習 → 反映
│   ├── scripts/
│   │   ├── optimize_params_with_optuna.py
│   │   ├── apply_best_params.py
│   │   ├── apply_best_params_to_metaai.py
│   │   ├── run_veritas_generate_dag.py       # ✅ GUI経由でveritas起動
│   │   └── log_utils.py                      # JSONログ出力ユーティリティなど
│   └── logs/
│       └── noctria_decision.log
│
├── core/
│   ├── noctria.py                     # 王Noctriaの統合判断クラス
│   ├── logger.py                      # ログ設定（XCom含む）
│   ├── reward.py                      # 強化学習用報酬関数
│   └── news_sentiment_fetcher.py      # ファンダ or センチメント取得
│
├── strategies/
│   ├── aurus_singularis.py
│   ├── levia_tempest.py
│   ├── prometheus_oracle.py
│   ├── noctus_sentinella.py
│   └── veritas_generator.py          # Veritasによる戦略生成AI
│
├── institutions/
│   └── central_bank_ai.py            # ファンダ分析を担う仮想中央銀行AI
│
├── envs/
│   ├── meta_ai_env_with_fundamentals.py
│   ├── metaai_env_sentiment.py
│   └── metaai.py                     # MetaAI環境本体（統合学習／推論用）
│
└── data/
    └── preprocessed_usdjpy_with_fundamental.csv
