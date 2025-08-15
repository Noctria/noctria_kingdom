<!-- AUTODOC:BEGIN mode=file_content path_globs=/mnt/d/noctria_kingdom/docs/_partials_full/docs/data_handling.md -->
# 📈 データ処理・学習パイプライン

## 📊 データソース

- Yahoo Finance: USDJPY ヒストリカル
- FRED API: GDP, CPI, FFR, 失業率
- NewsAPI + OpenAI: センチメント評価

## 🔄 前処理フロー

1. `fetch_and_clean_fundamentals.py`
2. `preprocess_usdjpy_data.py`
3. 統合データ出力: `preprocessed_usdjpy_with_fundamental.csv`

## 🧠 学習・最適化スクリプト

- PPO強化学習: `meta_ai_tensorboard_train.py`
- Optuna最適化:
  - `optimize_params.py`
  - `optimize_params_with_optuna.py`
<!-- AUTODOC:END -->
