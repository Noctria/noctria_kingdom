<!-- AUTODOC:BEGIN mode=file_content path_globs=/mnt/d/noctria_kingdom/docs/_partials_full/docs/optimization_notes.md -->
# 🎯 強化学習・パラメータ最適化ログ

## 🤖 強化学習（PPO）

- 環境ファイル: `meta_ai_env.py`, `meta_ai_env_with_fundamentals.py`
- カスタム報酬関数内容:
  - 利益の最大化
  - ドローダウン最小化
  - 勝率閾値ボーナス
  - 安定性（標準偏差）ボーナス
- ログ保存先: `ppo_tensorboard_logs/`

## 🧪 パラメータ最適化（Optuna）

- 最適化対象:
  - TP / SLの幅
  - ロットサイズ制御ルール
  - エントリー/フィルターの閾値
- 出力: `logs/best_params.json`
- 適用スクリプト:
  - `apply_best_params.py`
  - `apply_best_params_to_metaai.py`
<!-- AUTODOC:END -->
