!===========
/opt/airflow
├── dags/
│   ├── aurus_strategy_dag.py               # トレンド戦略（Aurus）
│   ├── levia_strategy_dag.py               # スキャルピング戦略（Levia）
│   ├── noctus_strategy_dag.py              # リスク戦略（Noctus）
│   ├── prometheus_strategy_dag.py          # 長期予測戦略（Prometheus）
│   ├── meta_ai_dag.py                      # MetaAI（意思統合 or 強化学習）
│   ├── noctria_kingdom_dag.py              # Noctria王国全体の戦略統括DAG
│   └── noctria_royal_dag.py                # 👑 王Noctriaの統合意思決定DAG
│
├── data/
│   └── preprocessed_usdjpy_with_fundamental.csv  # 統合済みテクニカル＋ファンダデータ
│
├── core/
│   ├── meta_ai.py                          # MetaAI（PPOによる進化統合）
│   ├── noctria.py                          # 👑 Noctria王の戦略判断ロジック
│   ├── risk_management.py                  # リスク計算や異常検知モジュール
│   └── central_bank_ai.py                  # 🏛️ 中央銀行AI（地政学・政策評価など）
│
├── strategies/
│   ├── Aurus_Singularis.py                 # 📈 Aurusのトレンド分析AI
│   ├── Levia_Tempest.py                    # ⚡ Leviaの短期スキャルピングAI
│   ├── Noctus_Sentinella.py                # 🛡️ Noctusのリスク監視AI
│   └── Prometheus_Oracle.py               # 🔮 Prometheusの予測・ファンダAI
│
└── logs/                                   # Airflowログ用ディレクトリ
