noctria-kingdom-main/
├── core/                        # 🌟 プロジェクトの中核機能群
│   ├── config.yaml              # 🌟 全体設定（YAML形式）
│   ├── config_loader.py         # 🔧 .envやYAMLの読み込みローダー
│   ├── logger.py                # 📜 ログ出力ユーティリティ
│   ├── NoctriaEnv.py            # 🧠 NoctriaMasterAIの環境定義（OpenAI Gym互換）
│   ├── risk_management.py       # 📊 共通リスク管理ロジック
│   ├── task_scheduler.py        # ⏰ バッチ実行スケジューラ
│   └── utils.py                 # 🛠️ 汎用ユーティリティ関数
│
├── data/                        # 📈 データ取得・加工・解析
│   ├── fetchers/                # 🌐 外部データ取得系
│   │   ├── market_data.py       # 📊 市場データAPI取得
│   │   ├── fundamental_analysis.py # 📰 経済指標やニュース分析
│   │   └── tradingview_fetcher.py  # 📈 TradingViewなど外部データ取得
│   ├── processors/              # 🔄 データ整形・前処理
│   │   ├── processed_data_handler.py # データ正規化・保存
│   │   ├── raw_data_loader.py      # ローデータ読み込み
│   │   └── sentiment_analysis.py   # SNS/ニュースのセンチメント解析
│   ├── anomaly_detection.py     # 🚨 異常値検知（IsolationForestなど）
│   ├── explainable_ai.py        # 💡 SHAPなどXAI可視化ロジック
│   ├── ensemble_learning.py     # 🤝 モデルアンサンブル手法
│   ├── institutional_order_monitor.py # 🏦 機関投資家フロー解析
│   ├── market_regime_detector.py# 📈 市場レジーム判定
│   └── quantum_computing_integration.py # ⚛️ 量子予測・シグナル生成
│
├── execution/                   # 💹 実際の発注・実行層
│   ├── challenge_monitor.py     # 🏆 長期パフォーマンス監視
│   ├── execution_manager.py     # ⚙️ 発注全体管理ハブ
│   ├── optimized_order_execution.py # 🧠 発注の最適化アルゴリズム
│   ├── order_execution.py       # 💼 基本的な発注クラス
│   ├── risk_control.py          # 🛡️ 執行段階のリスク管理
│   └── trade_monitor.py         # 📊 取引結果モニタリング
│
├── strategies/                  # 🧠 AI戦略ロジック群
│   ├── base/                    # 🏗️ 戦略基盤・共通化クラス
│   │   └── strategy_base.py
│   ├── reinforcement/           # 🚀 強化学習戦略群
│   │   └── reinforcement_learning.py # DQN/PPO/DDPGなど
│   ├── evolutionary/            # 🧬 進化的アルゴリズム
│   │   └── evolutionary_algorithm.py
│   ├── quantum/                 # ⚛️ 量子コンピューティング予測
│   │   └── quantum_prediction.py
│   ├── adaptive_trading.py      # ⚙️ 環境適応トレード戦略
│   ├── auto_adjustment.py       # 🔧 自動パラメータ調整
│   ├── portfolio_optimizer.py   # 💼 ポートフォリオ最適化戦略
│   ├── market_analysis.py       # 🔍 市場全体の分析ロジック
│   ├── strategy_optimizer_adjusted.py # 🛠️ 調整型戦略最適化
│   ├── strategy_runner.py       # 🎛️ 戦略実行・切替管理
│   ├── Aurus_Singularis.py      # 🦁 戦略: Aurus Singularis
│   ├── Levia_Tempest.py         # 🌊 戦略: Levia Tempest
│   ├── Noctus_Sentinella.py     # 🦉 戦略: Noctus Sentinella
│   └── Prometheus_Oracle.py     # 🔥 戦略: Prometheus Oracle
│
├── EA_Fintokei/                 # ⚙️ Fintokei専用EA群
│   ├── config/                  # ⚙️ EA設定・ルール群
│   │   ├── fintokei_config.yaml     # Fintokei設定パラメータ
│   │   ├── disqualification_rules.yaml # Fintokei失格条件
│   │   └── prohibited_actions.yaml     # 禁止事項
│   ├── scripts/                 # 📜 MQL5 EAコード
│   │   └── fintokei_trader.mq5      # 実際に稼働するEA
│   ├── docs/                    # 📖 ルール/仕様ドキュメント
│   └── README.md                # 💡 ディレクトリ概要
│
├── Noctria-GUI/                 # 🌟 Web可視化・API GUI
│   ├── backend/                 # ⚙️ FastAPIなどのバックエンド
│   ├── frontend/                # 🖥️ Dash/Streamlit UI
│   ├── shared/                  # 🌍 共通設定・コンポーネント
│   ├── ci/                      # 🔄 CI/CD設定
│   ├── docs/                    # 📖 GUI関連ドキュメント
│   └── README.md
│
├── models/                      # 🧠 学習済みモデル保存ディレクトリ
│   ├── reinforcement/           # 🤖 DQN/PPO/DDPGなど強化学習モデル
│   ├── evolutionary/            # 🧬 進化的アルゴリズムモデル
│   ├── quantum/                 # ⚛️ 量子予測モデル
│   └── README.md                # 💡 モデル管理方針ドキュメント
│
├── interfaces/                  # 🔌 Python⇔EA通信インターフェース
│   ├── api_server.py            # 🖥️ FastAPIサーバー（シグナル配信）
│   ├── websocket_bridge.py      # 🔄 WebSocketリアルタイム送信
│   ├── file_signal_writer.py    # 📝 ファイルベースシグナル出力
│   └── README.md                # 💡 各インターフェース解説
│
├── database/                    # 🗄️ DB管理・取引履歴
│   ├── db_connector.py          # 🔗 DB接続管理（例: SQLite, PostgreSQL）
│   ├── trade_history_model.py   # 💾 トレード履歴モデル定義
│   └── README.md                # 📖 DB設計・運用方針
│
├── research/                    # 🔬 研究・新機能検証
│   ├── new_lstm_forecast.py     # 🔍 LSTM強化版の実験
│   ├── quantum_hybrid_test.py   # ⚛️ 量子ハイブリッド戦略検証
│   └── README.md                # 💡 研究記録・運用方針
│
├── optimization/                # ⚙️ 戦略最適化モジュール
│   └── reinforcement_learning.py # 🧠 強化学習の最適化ロジック
│
├── tests/                       # 🧪 各種テスト
│   ├── backtesting.py           # 📈 バックテスト
│   ├── stress_tests.py          # 💥 ストレステスト
│   ├── unit_tests.py            # 🧩 単体テスト
│   └── performance_tests.py     # 🚀 性能テスト
│
├── docs/                        # 📖 プロジェクトドキュメント
│   ├── api_reference.md
│   ├── architecture.md
│   ├── data_handling.md
│   ├── optimization_notes.md
│   ├── strategy_manual.md
│   └── README.md
│
├── docker/                      # 🐳 Docker関連ファイル
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker_tensorflow_gpu_setup.md
│
├── 0529progress.md              # 📝 進捗メモ・日報
├── 20250530.md                  # 📝 進捗メモ・日報
├── README.md                    # 📘 プロジェクト全体README
└── .env                         # ⚙️ 環境変数ファイル
