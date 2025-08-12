# 🧠 Model Card — Prometheus-PPO

**Model ID:** Prometheus-PPO  
**Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の「Prometheus Oracle」における **PPO（Proximal Policy Optimization）** ベースの連続アクション・ポリシーの仕様を**再現可能**かつ**安全**に運用するためのモデルカード。  
> 参照：`../architecture/Plan-Layer.md` / `../apis/Do-Layer-Contract.md` / `../qa/Testing-And-QA.md` / `../observability/Observability.md` / `../security/Security-And-Access.md` / `../risks/Risk-Register.md` / `../roadmap/Release-Notes.md`

---

## 1. 概要（Summary）
- **タスク**：中短期のシグナル生成（連続 `action ∈ [-1, 1]` → ロットへ変換）。  
- **入力**：`feature_df.parquet`（Plan 層、5m 足中心、リーク防止済）。  
- **出力**：`action`（売買強度）＋`confidence`（0..1）＋`rationale`（簡易メタ）。  
- **連携**：Do 層で **Noctus** が境界適用 → 最適化発注 → 監査/評価（Check）。  
- **位置づけ**：裁量は**King Noctria**、本モデルは助言（自動発注はガード下）。

---

## 2.  intended use / 非対象
- **Intended**：BTCUSDT/ETHUSDT（5m）における平常市場の短中期予測起点。  
- **非対象**：極端イベントの短期災害モード（Safemode 前提）、低流動銘柄、秒足スキャル（Levia 担当）。

---

## 3. データ & 特徴量（Plan 層準拠）
- **期間**：通常は直近 2 年（ロール更新時 3–6 ヶ月スライド）。  
- **前処理**：UTC 時系列、欠損は `max_fill_gap` 以内を F/BFill、リーク防止（rolling → shift）。  
- **特徴群（例）**：
  - 価格/収益：`ret_1/5/20`, `zscore_20/50`  
  - テクニカル：`RSI(14)`, `MACD(12,26,9)`, `ATR(14)`  
  - ボラ/流動性：`HV(20/60)`, `approx_spread`, `roll_vwap`  
  - フェーズ：`regime`, `vol_bucket`, `session_flag`  
- **正規化**：学習/推論とも `zscore_252` を基本（統計は学習窓で固定）。

---

## 4. モデル構造（Architecture）
- **Actor/Critic**：MLP（`[128, 128]` ReLU）×2。  
- **出力**：ガウシアンの `μ, logσ` を Tanh で `[-1,1]` にスクイーズ。  
- **オプション**：`LSTM(64)` を先頭に付与可能（`use_recurrence: true`）。  
- **正則化**：PPO クリッピング + Entropy、価値関数係数。

```mermaid
flowchart LR
  IN[Features (T x D)] --> ENC[Encoder (MLP/LSTM)]
  ENC --> ACT[Actor Head (μ, logσ) → tanh]
  ENC --> CRT[Critic Head (V)]
  ACT --> A[action ∈ [-1,1]]
  CRT --> V[value]
```

---

## 5. 強化学習設定（PPO）
- **目的**：リスク調整収益（Sharpe_adj）最大化。  
- **環境**：スプレッド/手数料/スリッページを**埋め込み**（擬似ブローカー）。  
- **ロール**：Walk-Forward（WFO）：Train → Valid → Test を時系列順で前進。

### 5.1 報酬関数（例）
- `r_t = pnl_t - λ_dd * dd_penalty_t - λ_tc * trade_cost_t - λ_pos * |Δposition_t|`
  - `pnl_t`：即時損益（手数料・推定スリッページ込み）  
  - `dd_penalty_t`：直近最大ドローダウンの増分ペナルティ  
  - `trade_cost_t`：約定コスト（fees + slippage model）  
  - `Δposition_t`：ポジション変更量の罰則（過剰トレード抑制）  
- 係数（初期値例）：`λ_dd=0.5, λ_tc=0.1, λ_pos=0.02`（`configs/model/prometheus_ppo.yml` で調整）

### 5.2 主要ハイパーパラメータ
| Param | 値（初期） | 説明 |
|---|---|---|
| `algo` | `ppo` | |
| `gamma` | 0.99 | 割引率 |
| `gae_lambda` | 0.95 | GAE |
| `clip_range` | 0.2 | PPO クリップ |
| `entropy_coef` | 0.003 | 探索 |
| `vf_coef` | 0.5 | 価値関数係数 |
| `lr` | 3e-4 | 学習率（Cosine decay） |
| `batch_size` | 4096 | サンプル/更新 |
| `n_epochs` | 10 | 更新エポック |
| `max_grad_norm` | 0.5 | 勾配クリップ |
| `seed` | 1337,1729,31415 | 再現性 |

---

## 6. 学習手順（Training Procedure）
1. **データ確定**：Plan 層の `feature_df.parquet` を WFO 分割で固定。  
2. **設定固定**：`prometheus_ppo.yml`（下記）と Git commit をタグづけ。  
3. **学習**：PPO を Valid で早期停止（Sharpe_adj 指標）。  
4. **テスト**：Test 区間を一度だけ評価 → ゴールデン保存（ハッシュ）。  
5. **シャドー**：stg で 10 営業日評価（`howto-shadow-trading.md`）。  
6. **段階導入**：7%→30%→100%（`Strategy-Lifecycle.md`）。

**設定例（抜粋）**
```yaml
# configs/model/prometheus_ppo.yml
data:
  symbols: ["BTCUSDT","ETHUSDT"]
  timeframe: "5m"
  features_spec: "configs/feature_spec.json"
  wfo:
    train: "2024-01-01..2025-03-31"
    valid: "2025-04-01..2025-06-30"
    test:  "2025-07-01..2025-08-11"
model:
  arch: {encoder: "mlp", hidden: [128,128], recurrence: {use: false, hidden: 64}}
  algo: "ppo"
  hyper:
    gamma: 0.99
    gae_lambda: 0.95
    clip_range: 0.2
    entropy_coef: 0.003
    vf_coef: 0.5
    lr: 0.0003
    batch_size: 4096
    n_epochs: 10
    max_grad_norm: 0.5
reward:
  lambda_dd: 0.5
  lambda_tc: 0.1
  lambda_pos: 0.02
runtime:
  seed: [1337,1729,31415]
  device: "auto"
  num_workers: 4
```

---

## 7. 推論 & 配信（Serving）
- **インターフェイス**：Plan → Prometheus → Do（`API.md`/`Do-Layer-Contract.md`）  
- **入力**：`features_dict.json` or 一括 `feature_df.parquet` の最新行。  
- **出力**（例）：
```json
{"action": 0.82, "confidence": 0.78, "ts": "2025-08-12T06:58:00Z",
 "meta": {"strategy":"Prometheus-PPO","regime":"trending","vol":"mid"}}
```
- **Do 層**：`proposed_qty = f(action, Noctus.policy)` で正規化 → 発注最適化。  
- **レイテンシ目標**：p95 ≤ 50ms（モデル推論単体）。

---

## 8. 評価（Validation & Metrics）
- **オフライン**：WFO Test で `Sharpe_adj / Sortino / MaxDD / WinRate / Turnover / P&L`。  
- **オンライン（シャドー）**：KPI 安定、`do_order_latency p95` 劣化なし、`risk_events_total` 0。  
- **本番（カナリア）**：段階ごとに KPI を 3 営業日観測、重大アラート 0。  

**評価出力（例）**
```json
{
  "env": "stg",
  "window": "2025-07-01..2025-08-11",
  "metrics": {
    "sharpe_adj": 1.08,
    "sortino": 1.45,
    "max_drawdown_pct": 7.9,
    "win_rate": 0.52,
    "turnover": 0.74
  },
  "seed": 1337,
  "git": "abc1234",
  "spec": "configs/model/prometheus_ppo.yml"
}
```

---

## 9. ガードレール（Safety & Risk）
- **Noctus 境界**：`max_position_qty`, `max_drawdown_pct`, `max_slippage_pct` を**強制**。  
- **Safemode**：`flags.risk_safemode=true` で境界 0.5x。  
- **抑制**：`global_trading_pause` を Ops/Risk が制御。  
- **Non-Negotiables**：境界バイパスは**禁止**（`Security-And-Access.md`）。

---

## 10. 監視（Observability）
- **ドリフト**：`sigma_mean/sigma_std`（action 分布）・`hit_rate`・`turnover` を監視。  
- **アラート例**：
```promql
# アクション分布の平均が不自然（過去7d比）
abs((model_action_mean - scalar(avg_over_time(model_action_mean[7d]))))
  > 0.2
```
- **注釈**：採用/ロールバック/報酬調整を Grafana 注釈へ。

---

## 11. 再現性（Reproducibility）
- **固定物**：`feature_spec.json` / `prometheus_ppo.yml` / seeds / Git SHA / 依存バージョン。  
- **成果物**：`artifacts/models/prometheus/1.0/` に `model.bin`, `scaler.pkl`, `report.json`。  
- **ハッシュ**：ファイルごとに SHA256 を付与、`audit` へ記録。

---

## 12. 限界 & 既知の課題（Limitations）
- 市場レジーム急変時に反応遅延（`Risk-Register R-01`）。  
- スプレッド/スリッページモデルの**外挿弱さ**（極端時は過小/過大推定）。  
- LSTM 併用時の**過学習**（短窓で顕著）→ 早期停止・正則化を強める。

---

## 13. ライフサイクル & ゲーティング（Strategy-Lifecycle）
- **G0（起案）** → **G1（WFO合格）** → **G2（stg シャドー10日）** → **G3（prod 7%）** → **G4（30%→100%）**。  
- ロールバック：`howto-rollback.md`、インシデントは `Incident-Postmortems.md`。

---

## 14. API 連携（抜粋）
- **Plan トリガ**：`POST /api/v1/plan/collect`  
- **KPI 取得**：`GET /api/v1/check/kpi/summary`  
- **発注**：`POST /api/v1/do/orders`（`order_request.schema.json` 準拠）

---

## 15. スキーマ & サンプル（I/O）
```json
// 推論レスポンス（simplified）
{
  "action": -0.35,
  "confidence": 0.62,
  "ts": "2025-08-12T06:55:00Z",
  "meta": {"strategy":"Prometheus-PPO","symbol":"BTCUSDT","tf":"5m"}
}
```

---

## 16. セキュリティ & 倫理
- **PII/Secrets** を学習/ログに含めない。  
- 市場操作に該当する可能性のある**過剰な高速売買**は非対象（Levia に分離）。  
- 意思決定は常に **King Noctria** の統治下（説明責任：Hermes）。

---

## 17. 変更管理（Docs-as-Code）
- 学習/報酬/境界の変更は、**本カード/Config/Runbooks/Observability/API** を**同一PR**で更新。  
- 破壊的変更は ADR を起票、`Release-Notes.md`へ記録。

---

## 18. 変更履歴（Changelog）
- **2025-08-12**: v1.0 初版作成（PPO構成/報酬/学習/評価/安全/監視/再現性）
