# 🧠 Model Card — Prometheus (PPO)

**Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：Prometheus（PPOベースの戦略生成/予測モデル）の**仕様・学習設定・評価・安全策**を一元化し、再現性と説明責任を担保する。  
> 関連：`../governance/Vision-Governance.md` / `../architecture/Architecture-Overview.md` / `../models/Strategy-Lifecycle.md` / `../operations/Runbooks.md` / `../operations/Airflow-DAGs.md` / `../operations/Config-Registry.md`

---

## 1. モデル概要（What & Why）
- **名称**：Prometheus（Algorithm: PPO – Proximal Policy Optimization）
- **役割**：中短期の**方向・強度**シグナル生成（例：-1〜+1 の連続アクションをロット変換）
- **入力**：Plan層の特徴量（テクニカル/ボラ/出来高/市場イベント派生）  
- **出力**：`action ∈ [-1, 1]`（売買バイアス）＋**不確実性スコア**（σ）  
- **統治との接続**：King の意思決定素材。Noctus がロット・リスク境界に変換

---

## 2. 想定用途 / 非用途（Intended / Out-of-Scope）
**用途**  
- 平日マーケットの**5分足〜1時間足**での方向シグナル  
- 統治フロー内の**提案エージェント**として、Aurus/Levia/Veritas と併存

**非用途**  
- 超高頻度（サブ秒）スキャルピング単独運用  
- 大きなファンダメンタル変動（決算/規制）の即時対応の**単独判断**  
- 単独でのリスク裁定（Noctus を必須）

---

## 3. アーキテクチャ（Architecture）
- **アルゴリズム**：PPO（clip, GAE, value function + policy network）  
- **ポリシー**：2層 MLP（例：256→128）＋Tanh 出力、LayerNorm あり  
- **価値関数**：ポリシーと共有のバックボーン／分岐ヘッド  
- **観測**：標準化済み特徴量ベクトル（例：64〜160 次元）  
- **行動**：連続アクション（-1..1）→ Noctus がロットにマッピング  
- **報酬設計**：PnL正規化 − λ1*DDペナルティ − λ2*手数料 − λ3*ポジ過多抑制  
- **正則化**：Entropy bonus（行動多様性）/ Action L2（急変抑制）

---

## 4. データ（Data）
- **期間**：直近 3〜5 年（資産クラスにより可変）  
- **粒度**：5m / 15m / 1h  
- **特徴量例**：  
  - 価格系：OHLC、リターン、リターンの移動統計（μ, σ, Z）  
  - テクニカル：RSI、MACD、Stoch、ATR、Donchian、ADL  
  - ボラ・流動性：HV（20/60）、近似スプレッド、出来高変化率  
  - イベント：市場カレンダー（営業/祝日）、先行指標フラグ  
- **前処理**：欠損補完、Winsorize、標準化（rolling fit）、リーク防止（未来参照禁止）  
- **データ分割**：時系列順の**WFO（Walk-Forward Optimization）**：Train → Valid → Test（順次ずらし）

---

## 5. 学習設定（Training Setup）
- **ライブラリ**：PyTorch / RLlib（または Stable-Baselines3 同等）  
- **ハイパラ（例）**  
  - `learning_rate: 3e-4` / `gamma: 0.99` / `gae_lambda: 0.95`  
  - `clip_range: 0.2` / `entropy_coef: 0.01` / `vf_coef: 0.5`  
  - `n_steps: 2048` / `batch_size: 4096` / `epochs: 10`  
- **探索**：Optuna/TPE で 50〜200 試行、目的関数＝`Sharpe_adj`（DDペナルティ付き）  
- **早期終了**：Validation シャープの改善停滞（Δ<1% を N ラウンド）  
- **シード**：`[1337, 1729, 31415]`（再現性確保のため固定）

---

## 6. 評価方法（Evaluation Protocol）
- **バックテスト**（手数料/スリッページ込み）  
- **WFO**：ロールごとに学習→検証→テスト、ロール間のリーク遮断  
- **メトリクス**：`win_rate`, `max_dd`, `avg_r`, `Sharpe`, `Sortino`, `Calmar`, `payoff_ratio`  
- **有意性**：ブートストラップで信頼区間／ランダム戦略との差分検定  
- **実運用前テスト**：ステージングで 10〜15 営業日の**シャドー運用**

---

## 7. ベンチマーク（サンプル・フォーマット）
| ロール | 期間 | Sharpe | MaxDD | WinRate | Trades | AvgR |
|---|---|---:|---:|---:|---:|---:|
| WFO-1 | 2024Q1 | 1.34 | 4.8% | 0.56 | 410 | 0.12 |
| WFO-2 | 2024Q2 | 1.21 | 5.2% | 0.54 | 395 | 0.11 |
| Test | 2024Q3 | 1.08 | 6.1% | 0.53 | 380 | 0.10 |

> ※ 実値は `pdca_check_flow` の評価出力（`kpi_summary.json`）を反映。

---

## 8. デプロイ/推論（Inference & Serving）
- **実行**：`oracle_prometheus_infer_dag`（Airflow、UTC `0 6 * * 1-5`）  
- **I/F**：Plan層の特徴量を受け、`prometheus_oracle.py: predict_future()` で推論  
- **出力**：`signal.jsonl`（timestamp, symbol, action, sigma, model_version）  
- **統治**：Noctus が `action, sigma` をロット/SL/TP に変換 → Do層へ

---

## 9. リスクとバイアス（Risks & Biases）
- **Regime Shift**：相場レジームの変化に弱い → §10 の**Safemode**で露出縮小  
- **Data Bias**：特定ボラ環境への過適合 → WFO と Entropy で緩和  
- **Latency**：特定ブローカーで約定遅延 → Do層の最適発注（分割/タイミング）必須  
- **Leakage**：時間軸混在のリーク → ローリング標準化と厳格な学習/評価分離

---

## 10. 安全策（Safety & Guardrails）
- **Noctus の Non-Negotiables**：  
  - `max_drawdown_pct`, `stop_loss_pct`, `take_profit_pct`, `cooldown_minutes` を**越境禁止**  
  - 連敗/スリッページ閾値超過 → **自動停止（global_trading_pause）**  
- **Safemode**：`risk_safemode: true` 時は**リスク境界を半分**に縮小  
- **監査**：Do層は **`audit_order.json`** を**全件**保存（再現性）

---

## 11. 可観測性（Observability）
- **ログ**：推論ログ（入力hash/出力/所要時間/モデルID）  
- **メトリクス**：`inference_latency_ms`, `action_abs_mean`, `sigma_mean`  
- **アラート**：`sigma_mean` が低すぎ/高すぎ（行動が偏る/無力）→ Slack `#ops-alerts`

---

## 12. バージョニング & アーティファクト（Registry）
- **モデル保存先**：`/models/prometheus/{version}/`（例：`1.0.0/`）  
- **同梱物**：`model.pt`, `feature_spec.json`, `preprocess.pkl`, `training_config.yaml`, `eval_report.json`  
- **バージョニング規約**：`MAJOR.MINOR.PATCH`（Strategy-Lifecycle に準拠）

---

## 13. 再現手順（Repro Steps）
```bash
# 1) 特徴量生成（Plan）
python -m src.plan_data.features --symbols BTCUSDT,ETHUSDT --tf 5m --out /data/plan/features.parquet

# 2) 学習（PPO）
python -m src.prometheus_oracle.train \
  --config configs/prometheus/train.yaml \
  --features /data/plan/features.parquet \
  --out /models/prometheus/1.0.0

# 3) 評価（Check）
python -m src.check.evaluation /data/execution_logs /data/pdca_logs/kpi/ Aurus 2025-07-01 2025-08-01

# 4) 推論（Infer DAG と同等のローカル実行）
python -m src.prometheus_oracle.infer --model /models/prometheus/1.0.0 --features latest.parquet --out signal.jsonl
```

---

## 14. 制限事項 / Known Issues
- 低流動性銘柄ではシグナルがノイジー → シンボル除外/ロット縮小  
- 直近の制度変更・広域障害は扱えない → Ops/Runbooks の判断を優先  
- 長期ドローダウン期間の挙動に不確実性 → Act層の再評価を頻繁に回す

---

## 15. 変更履歴（Changelog）
- **2025-08-12**: 初版作成（PPO仕様/学習設定/評価/安全策/再現手順）

