```plaintext
📁 最新のツリー構造（機能説明付き）
ルート直下
.gitignore … Git管理除外設定

README.md … プロジェクト概要

callmemo_20250602.md, 0529progress.md, 20250530.md, 20250603.md … 進捗・議事メモ

Dockerfile … Dockerイメージビルドファイル

cpu.packages.txt, cpu.requirements.txt … Dockerビルド時のCPUパッケージ定義

docker use.md, docker_tensorflow_gpu_setup.md … Docker操作/セットアップドキュメント

requirements.txt … Python依存パッケージ

how-to-use-git.md, latest_tree_and_functions.md … Git操作・機能まとめ

token … （おそらく）APIトークンファイル

📂 EA_Strategies
各EAモジュール（MQL5スクリプト）

Aurus_Singularis, Levia_Tempest, Noctus_Sentinella, Prometheus_Oracle

📂 Noctria-GUI
Noctriaの可視化GUIフロント・バックエンド

.gitignore, README.md, docker-compose.yml

backend/ … APIサーバ（FastAPI等）

frontend/ … Dash/Streamlitなど

ci/github-actions/ … CI/CD設定

docs/, shared/, logs/

📂 core
Noctria統合AIシステムの中核コード

Noctria.py, NoctriaEnv.py … 環境クラス/統合AI管理クラス

config.yaml, logger.py, utils.py, task_scheduler.py, risk_management.py など

📂 data
データ取得・分析・XAI・量子計算まで多層的に担当

market_data_fetcher.py, sentiment_analysis.py … データ収集

ensemble_learning.py, explainable_ai.py, lstm_data_processor.py … AI解析

quantum_computing_integration.py … 量子計算統合！

📂 execution
注文執行・リスク制御など取引実務層

trade_monitor.py, trade_analysis.py … 履歴分析・監視

save_model_metadata.py, switch_to_best_model.py … モデル管理・切り替え

execution_manager.py, order_execution.py, optimized_order_execution.py, risk_control.py, challenge_monitor.py

📂 experts
MT5向けMQL5スクリプト

aurus_singularis.mq5, auto_evolution.mq5, core_EA.mq5, levia_tempest.mq5, noctus_sentinella.mq5, prometheus_oracle.mq5, quantum_prediction.mq5

📂 optimization
強化学習/AI最適化の主力

reinforcement_learning.py

📂 strategies
AI/EA戦略群（Python実装）

Aurus_Singularis.py, Levia_Tempest.py, NoctriaMasterAI.py, Noctus_Sentinella.py, Prometheus_Oracle.py … 各戦略AI

adaptive_trading.py, auto_adjustment.py, market_analysis.py, portfolio_optimizer.py, quantum_prediction.py, strategy_optimizer_adjusted.py, strategy_runner.py

reinforcement/ … DQN・経験リプレイ等の強化学習

evolutionary/, portfolio/ … 進化計算・ポートフォリオ管理

📂 tests
ユニットテスト/バックテスト/統合テスト群

backtesting.py, dqn_backtest.py, stress_tests.py, unit_tests.py, integration_test_noctria.py, test_mt5_connection.py, test_noctria_master_ai.py, など

📂 logs
trade_history_2025-05-31_to_2025-06-07.csv … 取引履歴CSV

（cron.logなど、運用ログもここに配置想定）

⚡️ 特徴的な構造ポイント
✅ Noctria Kingdom全体の戦略層（strategies）、取引層（execution）、学習層（optimization）を明確分離
✅ GUI層（Noctria-GUI）とコアAI層を独立管理
✅ MQL5 EAとPython戦略を両立し、柔軟な戦略運用が可能
