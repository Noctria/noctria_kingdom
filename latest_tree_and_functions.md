```plaintext
noctria-kingdom-main/
├── .gitignore                          # Git除外設定
├── 0529progress.md                     # 5/29進捗メモ
├── 20250530.md                         # 5/30進捗・議事録
├── 20250603.md                         # 6/3進捗・議事録
├── callmemo_20250602.md                # 6/2 通話メモ
├── README.md                           # プロジェクト概要
├── docker use.md                       # Docker運用メモ
├── docker_tensorflow_gpu_setup.md      # TensorFlow GPUセットアップ手順
├── how-to-use-git.md                   # Git利用メモ
├── latest_tree_and_functions.md        # 最新ツリー＆機能一覧
│
├── core/                               # 🌟 Noctria Kingdomのコア機能
│   ├── Noctria.py                      # 👑 中枢管理モジュール（意思決定AI統括）
│   ├── config.yaml                     # ⚙️ 設定ファイル
│   ├── init.py                         # 🛠️ 初期化スクリプト
│   ├── logger.py                       # 📜 ロギング機能
│   ├── risk_management.py              # 🛡️ リスク管理ロジック
│   ├── task_scheduler.py               # ⏰ タスクスケジューラ
│   └── utils.py                        # 🛠️ 汎用ユーティリティ
│
├── data/                               # 📈 データ取得・解析モジュール
│   ├── anomaly_detection.py            # 🚨 異常検知
│   ├── data_loader.py                  # 📦 データ読み込み・整形
│   ├── ensemble_learning.py            # 🤝 アンサンブル学習
│   ├── explainable_ai.py               # 💡 XAI透明性向上
│   ├── fundamental_analysis.py         # 📰 ファンダ分析
│   ├── high_frequency_trading.py       # ⚡ HFTアルゴリズム
│   ├── institutional_order_monitor.py  # 🏦 機関投資家監視
│   ├── lstm_data_processor.py          # 🧠 LSTM用データ整形
│   ├── market_data_fetcher.py          # ✅ 市場データ取得
│   ├── market_regime_detector.py       # 🏷️ 市場局面検出
│   ├── multi_objective_optimizer.py    # 🎯 多目的最適化
│   ├── processed_data_handler.py       # 🔄 加工済データ管理
│   ├── quantum_computing_integration.py# ⚛️ 量子コンピュータ連携
│   ├── raw_data_loader.py              # 📂 生データ取得
│   ├── sentiment_analysis.py           # 🗣️ センチメント分析
│   └── tradingview_fetcher.py          # 📈 TradingView API連携
│
├── execution/                          # ⚙️ 実行・取引管理
│   ├── challenge_monitor.py            # 🏆 戦略パフォーマンス監視
│   ├── execution_manager.py            # 🎛️ 注文実行全体管理
│   ├── optimized_order_execution.py    # 🧠 最適化された発注
│   ├── order_execution.py              # 💼 注文執行
│   ├── risk_control.py                 # 🛡️ リスク制御
│   └── trade_monitor.py                # 📊 トレード状況監視
│
├── strategies/                         # 🧩 戦略モジュール群
│   ├── Aurus_Singularis.py             # 🦁 戦略Aurus Singularis
│   ├── Levia_Tempest.py                # 🌊 戦略Levia Tempest
│   ├── NoctriaMasterAI.py              # 👑 戦略統括AI
│   ├── Noctus_Sentinella.py            # 🦉 戦略Noctus Sentinella
│   ├── Prometheus_Oracle.py            # 🔥 戦略Prometheus Oracle
│   ├── adaptive_trading.py             # 🔧 適応型戦略
│   ├── auto_adjustment.py              # 🔄 自動調整
│   ├── market_analysis.py              # 📊 市場分析
│   ├── portfolio/                      # 💼 ポートフォリオ最適化
│   │   └── portfolio_optimizer.py
│   ├── portfolio_optimizer.py          # 💼 ポートフォリオ管理
│   ├── quantum_prediction.py           # ⚛️ 量子予測戦略
│   ├── reinforcement/                  # 🚀 強化学習モジュール
│   │   ├── dqn_agent.py                # 🤖 DQNエージェント
│   │   ├── experience_replay.py        # 🔄 経験リプレイ
│   │   ├── exploration_strategy.py     # 🧭 探索戦略
│   │   ├── huber_loss.py               # ⚖️ Huber損失
│   │   ├── prioritized_experience_replay.py # 🔥 優先度付きリプレイ
│   │   └── target_network.py           # 🎯 ターゲットネットワーク
│   ├── reinforcement_learning.py       # 🚀 強化学習アルゴリズム
│   ├── self_play.py                    # 🤼‍♂️ 自己対戦学習
│   ├── strategy_optimizer_adjusted.py  # ⚙️ 戦略最適化
│   └── strategy_runner.py              # 🎛️ 戦略実行管理
│
├── experts/                            # ⚡ MQL5 EA群
│   ├── aurus_singularis.mq5
│   ├── auto_evolution.mq5
│   ├── core_EA.mq5
│   ├── levia_tempest.mq5
│   ├── noctus_sentinella.mq5
│   ├── prometheus_oracle.mq5
│   └── quantum_prediction.mq5
│
├── EA_Strategies/                      # 🏰 各EA戦略の補助ディレクトリ
│   ├── Aurus_Singularis
│   ├── Levia_Tempest
│   ├── Noctus_Sentinella
│   └── Prometheus_Oracle
│
├── Noctria-GUI/                        # 🎨 GUIシステム全体
│   ├── .gitignore
│   ├── README.md
│   ├── backend/                        # 🖥️ APIサーバー
│   │   ├── Dockerfile
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── main.py
│   │   │   ├── routes/config_router.py # 📡 設定APIルート
│   │   │   └── utils/util.py
│   │   ├── requirements.txt
│   │   └── tests/test_api.py
│   ├── ci/github-actions/              # 🔧 CI/CD
│   │   ├── cd.yml
│   │   └── ci.yml
│   ├── docker-compose.yml
│   ├── docs/                           # 📝 GUIドキュメント
│   │   ├── README.md
│   │   └── architecture.md
│   ├── frontend/                       # 🎨 フロントエンド
│   │   ├── Dockerfile
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── components/sample_component.py
│   │   │   └── dashboard.py
│   │   ├── requirements.txt
│   │   └── tests/test_dashboard.py
│   ├── logs/performance_log.csv        # 📊 GUIパフォーマンスログ
│   └── shared/configs/default_config.yaml # ⚙️ 共通設定
│
├── order_api.py                        # 📡 注文API機能
├── optimization/reinforcement_learning.py # 🚀 RL最適化アルゴリズム
│
├── tests/                              # 🧪 テスト群
│   ├── backtesting.py
│   ├── backtesting/dqn_backtest.py
│   ├── execute_order_test.py
│   ├── integration_test_noctria.py
│   ├── run_ai_trading_loop.py
│   ├── stress_tests.py
│   ├── test_dqn_agent.py
│   ├── test_mt5_connection.py
│   ├── test_noctria_master_ai.py
│   └── unit_tests.py
│
└── token                               # 🔑 （APIキー管理など？）
