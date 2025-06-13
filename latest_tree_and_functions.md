# 📂 Noctria Kingdom - Airflow プロジェクト構成

```
/opt/airflow
├── dags/                        # DAGスケジューラ関連
│   ├── aurus_strategy_dag.py         # 📈 Aurusのトレンド戦略DAG
│   ├── levia_strategy_dag.py         # ⚡ LeviaのスキャルピングDAG
│   ├── noctus_strategy_dag.py        # 🛡️ Noctusのリスク管理DAG
│   ├── prometheus_strategy_dag.py    # 🔮 Prometheusの予測DAG
│   ├── meta_ai_dag.py                # 🧠 MetaAI (統合強化学習) のDAG
│   ├── noctria_royal_dag.py          # 👑 王Noctriaの戦略判断DAG
│   └── noctria_kingdom_dag.py        # 🏰 王国全体の調和・実行DAG
│
├── data/
│   └── preprocessed_usdjpy_with_fundamental.csv  # USDJPYの前処理済みデータ
│
├── core/                       # 中核ロジック
│   ├── meta_ai.py              # 🧠 MetaAI本体（PPO強化学習）
│   ├── noctria.py              # 👑 Noctria王の統合戦略判断AI
│   ├── risk_management.py      # リスク管理・異常検知ロジック
│   └── central_bank_ai.py      # 🏛️ 中央銀行AI（ファンダ政策スコアリング）
│
├── strategies/                 # 各戦略AIユニット
│   ├── Aurus_Singularis.py     # 📈 トレンドAI（Aurus）
│   ├── Levia_Tempest.py        # ⚡ スキャルピングAI（Levia）
│   ├── Noctus_Sentinella.py    # 🛡️ リスクAI（Noctus）
│   └── Prometheus_Oracle.py    # 🔮 ファンダ・予測AI（Prometheus）
│
└── logs/                       # Airflowログ格納ディレクトリ
```
