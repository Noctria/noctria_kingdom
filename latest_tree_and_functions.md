```plaintext
(ここに、さっき出したコメント付きツリーをそのまま貼り付ける)

noctria-kingdom-main/
├── core/
│   ├── config.yaml                  # 🌟 システム全体の環境設定
│   ├── config_loader.py             # 🔧 設定ファイルを読み込むユーティリティ
│   ├── logger.py                    # 📜 ログ管理機能
│   ├── NoctriaEnv.py                # 🧠 NoctriaMasterAIの環境（Gym互換）
│   ├── risk_management.py           # 📊 リスク管理アルゴリズム（損失制御など）
│   ├── task_scheduler.py            # ⏰ 定期実行・バッチ処理管理
│   ├── utils.py                     # 🛠️ 汎用関数（ヘルパー関数など）
│   ├── explainable_ai.py            # 💡 SHAPなどで透明性向上（XAI機能）
│   ├── anomaly_detection.py         # 🚨 異常値検知アルゴリズム（例: Isolation Forest）
│   ├── NoctriaMasterAI.py           # 👑 NoctriaMasterAIクラス（今日拡張）
│       - 市場データ取得・LSTM予測・リスク管理などを統括
│
├── data/
│   ├── market_data.py               # 📈 市場データAPI取得（例: Binance, Alpha Vantage）
│   ├── fundamental_analysis.py      # 📰 経済指標やニュースの分析
│   ├── tradingview_fetcher.py       # 📈 TradingViewからデータ取得
│   ├── processed_data_handler.py    # 🔄 データの前処理・整形・保存
│   ├── raw_data_loader.py           # 📂 ローデータ読み込み（CSVなど）
│   ├── sentiment_analysis.py        # 🗣️ SNS・ニュースのセンチメント分析
│   ├── ensemble_learning.py         # 🤝 モデルアンサンブル学習
│   ├── institutional_order_monitor.py # 🏦 機関投資家の大口注文監視
│   ├── market_regime_detector.py    # 🏷️ 市場局面（ブル/ベア/レンジ）検知
│   ├── quantum_computing_integration.py # ⚛️ 量子コンピューティング統合
│   ├── market_data_fetcher.py       # ✅ ドル円専用化など実際のデータ取得機能（今日更新）
│   ├── lstm_data_processor.py       # 🆕 LSTM用データ整形クラス（今日新規追加）
│       - 取得データをLSTMの入力形状に加工
│
├── execution/
│   ├── challenge_monitor.py         # 🏆 各戦略の成績・勝率モニタリング
│   ├── execution_manager.py         # ⚙️ 注文発注フローの管理
│   ├── optimized_order_execution.py # 🧠 スリッページ抑制などの最適化発注
│   ├── order_execution.py           # 💼 実際の注文処理・執行
│   ├── risk_control.py              # 🛡️ リスク制御アルゴリズム（最大損失管理など）
│   ├── trade_monitor.py             # 📊 取引履歴や注文状況の監視
│
├── strategies/
│   ├── base/
│   │   ├── strategy_base.py         # 🏗️ 戦略基盤クラス（共通機能）
│   ├── reinforcement/
│   │   ├── reinforcement_learning.py # 🚀 強化学習戦略（DQN/PPO/DDPGなど）
│   │   ├── dqn_agent.py             # 🤖 DQNエージェント
│   │   ├── experience_replay.py     # 🔄 経験リプレイバッファ
│   │   ├── prioritized_experience_replay.py # 🔥 重要度サンプリング
│   │   ├── exploration_strategy.py  # 🧭 探索戦略（ε-greedyなど）
│   │   ├── huber_loss.py            # ⚖️ Huber Lossによる損失関数
│   ├── portfolio_optimizer.py       # 💼 ポートフォリオ最適化（市場適応型）
│   ├── strategy_runner.py           # 🎛️ 各戦略の切り替えと統合実行管理
│   ├── Aurus_Singularis.py          # 🦁 戦略Aurus Singularis
│   ├── Levia_Tempest.py             # 🌊 戦略Levia Tempest
│   ├── Noctus_Sentinella.py         # 🦉 戦略Noctus Sentinella
│   ├── Prometheus_Oracle.py         # 🔥 戦略Prometheus Oracle
│   └── Noctria.py                   # 👑 NoctriaMasterAI 中核管理（または戦略統括）
│
├── EA_Fintokei/
│   ├── config/
│   │   ├── fintokei_config.yaml     # ⚙️ Fintokei設定
│   │   ├── disqualification_rules.yaml # ❌ 失格条件設定
│   │   └── prohibited_actions.yaml  # 🚫 禁止行動設定
│   ├── scripts/
│   │   └── fintokei_trader.mq5      # 📜 MQL5 EAスクリプト
│   ├── docs/                        # 📚 Fintokei関連ドキュメント
│   └── README.md
│
├── tests/
│   ├── backtesting.py               # 📈 バックテスト（戦略検証）
│   ├── dqn_backtest.py              # 📈 DQN強化学習効果の可視化
│   ├── stress_tests.py              # 💥 システム負荷テスト
│   ├── unit_tests.py                # 🧩 単体テスト
│   ├── performance_tests.py         # 🚀 性能評価テスト
│
├── docs/
│   ├── api_reference.md             # 📜 APIリファレンス
│   ├── architecture.md              # 🏗️ システムアーキテクチャ図
│   ├── strategy_manual.md           # 📖 戦略マニュアル
│
├── Noctria-GUI/
│   ├── backend/                     # 🖥️ バックエンド
│   ├── frontend/                    # 🎨 フロントエンド
│   ├── shared/                      # 🧩 共通モジュール
│
├── docker/
│   ├── Dockerfile                   # 🐳 Dockerイメージビルド
│   ├── docker-compose.yml           # 🐳 コンテナオーケストレーション
│   ├── docker_tensorflow_gpu_setup.md # ⚙️ GPUセットアップ手順
│
└── README.md                        # プロジェクト概要・使い方
