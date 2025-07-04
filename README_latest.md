.
├── 0625引継ぎ書
├── 20250607update
├── 20250610議事録
├── 20250704_議事録
├── Dockerfile
├── README_latest.md
├── airflow_docker
│   ├── docker-compose.yaml
│   └── inspect_generated_files.py
├── core
│   └── path_config.py
├── cpu.packages.txt
├── cpu.requirements.txt
├── docs
│   ├── diagnostics
│   │   └── tree_snapshot.txt
│   └── misc
│       ├── 0529progress.md
│       ├── 20250530.md
│       ├── 20250603.md
│       ├── API_Keys.md
│       ├── AirFlow-pip-list.md
│       ├── AirFlow_start.md
│       ├── Airflow 3.0.2ベースでイメージを構築しよう.md
│       ├── README.md
│       ├── README_latest.md
│       ├── Tensor Boardの起動方法.md
│       ├── airflow-dockerイメージのバックアップと復元.md
│       ├── callmemo_20250602.md
│       ├── docker use.md
│       ├── docker_tensorflow_gpu_setup.md
│       ├── how-to-use-git.md
│       ├── latest_tree_and_functions.md
│       ├── tree_L3_snapshot.txt
│       └── カスタムAirflowイメージを作る.md
├── execution
│   ├── challenge_monitor.py
│   ├── execution_manager.py
│   ├── optimized_order_execution.py
│   ├── order_execution.py
│   ├── save_model_metadata.py
│   ├── switch_to_best_model.py
│   ├── tensorflow_task.py
│   ├── trade_analysis.py
│   ├── trade_monitor.py
│   └── trade_simulator.py
├── experts
│   ├── aurus_singularis.mq5
│   ├── auto_evolution.mq5
│   ├── core_EA.mq5
│   ├── levia_tempest.mq5
│   ├── noctus_sentinella.mq5
│   ├── prometheus_oracle.mq5
│   └── quantum_prediction.mq5
├── llm_server
│   ├── llm_prompt_builder.py
│   ├── main.py
│   ├── veritas_eval_api.py
│   └── veritas_llm_server.py
├── logs
│   ├── dependency_report.json
│   └── refactor_plan.json
├── mt5_test.py
├── noctria_gui
├── order_api.py
├── requirements.txt
├── setup.packages.sh
├── setup.python.sh
├── setup.sources.sh
├── system_start
├── tests
│   ├── backtesting.py
│   ├── cuda-keyring_1.1-1_all.deb
│   ├── execute_order_test.py
│   ├── forward_test_meta_ai.py
│   ├── integration_test_noctria.py
│   ├── run_ai_trading_loop.py
│   ├── stress_tests.py
│   ├── test_dqn_agent.py
│   ├── test_dummy.py
│   ├── test_floor_mod.py
│   ├── test_floor_mod_gpu.py
│   ├── test_meta_ai_env_rl.py
│   ├── test_meta_ai_rl.py
│   ├── test_meta_ai_rl_longrun.py
│   ├── test_meta_ai_rl_real_data.py
│   ├── test_mt5_connection.py
│   ├── test_noctria.py
│   ├── test_noctria_master_ai.py
│   ├── test_path_config.py
│   └── unit_tests.py
├── tools
│   ├── apply_path_fixes.py
│   ├── apply_refactor_plan.py
│   ├── apply_refactor_plan_v2.py
│   ├── cleanup_commands.sh
│   ├── dependency_analyzer.py
│   ├── diagnose_dependencies.py
│   ├── fix_path_violations.py
│   ├── generate_cleanup_script.py
│   ├── generate_github_template_summary.py
│   ├── generate_readme_summary.py
│   ├── generate_refactor_plan.py
│   ├── hardcoded_path_replacer.py
│   ├── refactor_manager.py
│   ├── reorganize_docs.py
│   ├── save_tree_snapshot.py
│   ├── scan_and_fix_paths.py
│   ├── scan_refactor_plan.py
│   ├── structure_auditor.py
│   ├── structure_refactor.py
│   └── verify_path_config_usage.py
├── veritas
│   ├── generate_strategy_file.py
│   ├── veritas_airflow_executor.py
│   └── veritas_generate_strategy.py
└── パス参照MAP

14 directories, 104 files
# 📘 Noctria Kingdom 最新構成 (tree -L 3)

```bash
```

## 🗂 各フォルダ概要
- `airflow_docker/`: Airflow本体・DAG群・Docker設定
- `execution/`: 実行・発注・監視ロジック群
- `experts/`: MQL5形式のEA戦略群
- `veritas/`: 戦略生成AIモジュール
- `llm_server/`: FastAPI経由のローカル推論サーバー
- `tools/`: 各種ツール・リファクタスクリプト
- `tests/`: ユニット・統合・ストレステスト群
- `docs/`: README、構成説明、セットアップ手順など
- `logs/`: 監査・評価ログ
