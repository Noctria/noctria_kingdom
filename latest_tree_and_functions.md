# 📂 Noctria Kingdom プロジェクト構造（2025-06-08）

├── .gitignore # Git管理除外設定
├── 0529progress.md # 2025/05/29進捗メモ
├── 20250530.md # 2025/05/30進捗メモ
├── 20250603.md # 2025/06/03進捗メモ
├── 20250607update # 2025/06/07更新メモ
├── Dockerfile # Dockerビルド設定（ベース環境）
├── EA_Strategies/ # EA群（MQL5戦略）
│ ├── Aurus_Singularis # 戦略EA: Aurus（黄金戦略）
│ ├── Levia_Tempest # 戦略EA: Levia（嵐の支配者）
│ ├── Noctus_Sentinella # 戦略EA: Noctus（闇の見張り）
│ ├── Prometheus_Oracle # 戦略EA: Prometheus（叡智の火）
├── FRED_API_Key # FRED APIキー格納
├── Noctria-GUI/ # Noctria用Web GUI
│ ├── .gitignore # GUI内のGit管理除外
│ ├── README.md # GUI概要説明
│ ├── backend/ # GUIバックエンド（FastAPI）
│ │ ├── Dockerfile
│ │ ├── app/
│ │ │ ├── init.py
│ │ │ ├── config.py # 設定管理
│ │ │ ├── main.py # FastAPI起動エントリ
│ │ │ ├── routes/config_router.py # APIルーティング
│ │ │ └── utils/util.py # 補助ツール
│ │ ├── requirements.txt # 依存パッケージ
│ │ ├── tests/test_api.py # APIテスト
│ ├── ci/github-actions/ # GitHub Actions CI/CD設定
│ │ ├── cd.yml
│ │ └── ci.yml
│ ├── docker-compose.yml # GUI開発環境
│ ├── docs/ # ドキュメント
│ │ ├── README.md
│ │ ├── architecture.md # GUIアーキテクチャ
│ ├── frontend/ # GUIフロントエンド
│ │ ├── Dockerfile
│ │ ├── app/
│ │ │ ├── init.py
│ │ │ ├── components/sample_component.py
│ │ │ ├── dashboard.py # ダッシュボード機能
│ │ ├── requirements.txt
│ │ ├── tests/test_dashboard.py
│ ├── logs/performance_log.csv # GUIパフォーマンスログ
│ ├── shared/configs/default_config.yaml
├── README.md # プロジェクト総合概要
├── callmemo_20250602.md # 2025/06/02作業メモ
├── core/ # MetaAIコアモジュール群
│ ├── Noctria.py # Noctria戦略AIクラス
│ ├── NoctriaEnv.py # 強化学習環境（Gym環境）
│ ├── config.yaml # AI設定ファイル
│ ├── init.py
│ ├── logger.py # ログ管理モジュール
│ ├── meta_ai.py # MetaAI（PPO強化学習統合）
│ ├── meta_ai_env.py # MetaAI環境定義
│ ├── risk_management.py # リスク管理ロジック
│ ├── task_scheduler.py # タスクスケジューラ
│ ├── utils.py # 汎用ユーティリティ
├── cpu.packages.txt # CPU版環境パッケージリスト
├── cpu.requirements.txt # CPU版Pythonパッケージ
├── data/ # データ処理関連
│ ├── anomaly_detection.py # 異常検知
│ ├── data_loader.py # データロード
│ ├── ensemble_learning.py # アンサンブル学習
│ ├── explainable_ai.py # AI説明可能性モジュール
│ ├── fundamental/ # ファンダメンタルデータ取得
│ │ ├── fetch_fred_data.py
│ │ └── fetch_fred_data_cleaned.py
│ ├── fundamental_analysis.py # ファンダ系解析
│ ├── high_frequency_trading.py # 高頻度取引
│ ├── institutional_order_monitor.py # 大口注文監視
│ ├── lstm_data_processor.py # LSTM用データ前処理
│ ├── market_data_fetcher.py # 市場データ取得
│ ├── market_regime_detector.py # 市場レジーム検知
│ ├── multi_objective_optimizer.py # 多目的最適化
│ ├── preprocessing/preprocess_usdjpy_1h.py # USDJPYデータ整形
│ ├── processed_data_handler.py
│ ├── quantum_computing_integration.py # 量子コンピューティング統合
│ ├── raw_data_loader.py
│ ├── sentiment_analysis.py
│ ├── tradingview_fetcher.py # TradingViewデータ取得
├── docker use.md # Docker活用メモ
├── docker_tensorflow_gpu_setup.md # Docker TensorFlow GPU設定手順
├── docs/ # 全体ドキュメント
│ ├── api_reference.md
│ ├── architecture.md
│ ├── data_handling.md
│ ├── optimization_notes.md
│ ├── strategy_manual.md
├── execution/ # 取引実行・監視層
│ ├── challenge_monitor.py
│ ├── execution_manager.py
│ ├── optimized_order_execution.py
│ ├── order_execution.py
│ ├── risk_control.py
│ ├── save_model_metadata.py
│ ├── switch_to_best_model.py
│ ├── trade_analysis.py
│ ├── trade_monitor.py
│ ├── trade_simulator.py
├── experts/ # EAソースコード（MQL5）
│ ├── aurus_singularis.mq5
│ ├── auto_evolution.mq5
│ ├── core_EA.mq5
│ ├── levia_tempest.mq5
│ ├── noctus_sentinella.mq5
│ ├── prometheus_oracle.mq5
│ ├── quantum_prediction.mq5
├── how-to-use-git.md # Git操作メモ
├── latest_tree_and_functions.md # 最新ツリーと機能メモ
├── logs/trade_history_2025-05-31_to_2025-06-07.csv # トレード履歴ログ
├── optimization/reinforcement_learning.py # PPO強化学習モジュール
├── order_api.py # 注文APIモジュール
├── requirements.txt
├── scripts/meta_ai_tensorboard_train.py # TensorBoard学習スクリプト
├── setup.packages.sh # Linuxパッケージセットアップ
├── setup.python.sh # Pythonセットアップ
├── setup.sources.sh # ソース取得スクリプト
├── strategies/ # 戦略モジュール群
│ ├── Aurus_Singularis.py
│ ├── Levia_Tempest.py
│ ├── NoctriaMasterAI.py
│ ├── Noctus_Sentinella.py
│ ├── Prometheus_Oracle.py
│ ├── adaptive_trading.py
│ ├── auto_adjustment.py
│ ├── evolutionary/evolutionary_algorithm.py
│ ├── market_analysis.py
│ ├── portfolio/portfolio_optimizer.py
│ ├── portfolio_optimizer.py
│ ├── quantum_prediction.py
│ ├── reinforcement/dqn_agent.py
│ ├── reinforcement/experience_replay.py
│ ├── reinforcement/exploration_strategy.py
│ ├── reinforcement/huber_loss.py
│ ├── reinforcement/prioritized_experience_replay.py
│ ├── reinforcement/reinforcement_learning.py
│ ├── reinforcement/target_network.py
│ ├── self_play.py
│ ├── strategy_optimizer_adjusted.py
│ ├── strategy_runner.py
├── system_start # 起動スクリプト？
├── tests/ # テスト群
│ ├── backtesting.py
│ ├── backtesting/dqn_backtest.py
│ ├── execute_order_test.py
│ ├── integration_test_noctria.py
│ ├── run_ai_trading_loop.py
│ ├── stress_tests.py
│ ├── test_dqn_agent.py
│ ├── test_meta_ai_env_rl.py
│ ├── test_meta_ai_rl.py
│ ├── test_meta_ai_rl_longrun.py
│ ├── test_meta_ai_rl_real_data.py
│ ├── test_mt5_connection.py
│ ├── test_noctria_master_ai.py
│ ├── unit_tests.py
├── token # APIトークンなど？
