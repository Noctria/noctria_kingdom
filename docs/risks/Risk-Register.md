# 🧨 Risk Register — Noctria Kingdom

**Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の運用・アルゴ・オーケストレーションに関わる**主要リスクを可視化し、閾値・監視・緩和策**を明文化する。  
> 参照：`../governance/Vision-Governance.md` / `../operations/Runbooks.md` / `../operations/Config-Registry.md` / `../operations/Airflow-DAGs.md` / `../observability/Observability.md` / `../security/Security-And-Access.md` / `../apis/Do-Layer-Contract.md` / `../incidents/Incident-Postmortems.md` / `../adrs/`

---

## 0. 使い方（How to Use）
1) 新規リスクは**テンプレ（§6）**で起票 → PR。  
2) 重大イベント発生時は **Incident** を起票し、**再発防止策**を本表へ反映。  
3) **月次レビュー**（Council）でスコアと緩和策の妥当性を見直す。  
4) 閾値/トグルは `../operations/Config-Registry.md` を**単一情報源（SoT）**とする。

---

## 1. スコアリング規約（Likelihood × Impact）
- **Likelihood（発生確率）**: 1=稀（年1以下） / 2=低（四半期1） / 3=中（月1） / 4=高（週1） / 5=非常に高（週複数）  
- **Impact（影響度）**: 1=軽微 / 2=小 / 3=中（部分停止・軽損失） / 4=大（1日停止・有意損失） / 5=重大（安全性/財務に深刻）  
- **Score = L × I**  
- **色分け**（許容度目安）:  
  - **Red** ≥ 15（**不可**：即時の恒久対策/運用抑制が必要）  
  - **Orange** 10–14（要管理：緩和策と監視を強化）  
  - **Yellow** 6–9（監視維持）  
  - **Green** ≤ 5（容認）

> **Non-Negotiables**（`Vision-Governance.md`）に抵触するものは、スコアに関わらず**Red扱い**。

---

## 2. トップリスク一覧（要約表）
| ID | タイトル | カテゴリ | オーナー | L | I | Score | 現状 | 次回見直し |
|---|---|---|---|:-:|:-:|:-:|---|---|
| R-01 | レジームシフト（相場構造変化） | 市場 | Risk(Noctus) | 4 | 5 | **20** | 監視強化・Safemode準備 | 2025-08-31 |
| R-02 | 流動性低下/スリッページ急騰 | 市場/実行 | Ops/Do | 3 | 4 | **12** | Slippage監視/段階停止 | 2025-08-20 |
| R-03 | ブローカー/API 障害 | 外部依存 | Ops | 3 | 5 | **15** | 代替経路/レート制限対策 | 2025-08-20 |
| R-04 | データ欠損/品質劣化（Plan） | データ | Plan | 3 | 4 | **12** | 欠損フラグ/再取得 | 2025-08-18 |
| R-05 | Clock Skew/時刻整合不良 | 時刻/運用 | Ops | 2 | 3 | 6 | NTP監視/UTC原則 | 2025-09-01 |
| R-06 | Idempotency破れ/重複発注 | 実行/設計 | Do | 2 | 5 | **10** | キー必須/監査照合 | 2025-08-20 |
| R-07 | リスク境界の誤設定/バイパス | ガバナンス | Risk | 2 | 5 | **10** | Config二重承認 | 2025-08-20 |
| R-08 | モデルドリフト/過学習 | モデル | Models | 3 | 4 | **12** | WFO/定期再評価 | 2025-08-31 |
| R-09 | スキーマドリフト（Plan→Do→Check） | I/F | Arch | 3 | 3 | 9 | JSONSchema CI | 2025-08-25 |
| R-10 | Secrets漏えい/鍵期限切れ | セキュリティ | Sec | 2 | 5 | **10** | Vault/90日ローテ | 2025-08-22 |
| R-11 | Airflow スケジューラ停止/滞留 | オーケストレーション | Ops | 3 | 4 | **12** | HealthCheck/Backfill手順 | 2025-08-18 |
| R-12 | バックフィル起因のI/O飽和 | パフォーマンス | Ops | 3 | 3 | 9 | スロットリング | 2025-08-25 |
| R-13 | Config/Flags ドリフト | 構成管理 | Ops | 3 | 3 | 9 | 同一PR更新 | 2025-08-20 |
| R-14 | 規制/コンプラ変更の未追随 | 法務/外部 | Gov | 2 | 4 | 8 | ウォッチ/ADR対応 | 2025-09-10 |
| R-15 | 祝日/営業カレンダー誤設定 | 運用/データ | Plan/Ops | 2 | 3 | 6 | 二重ソース照合 | 2025-09-01 |
| R-16 | PII/センシティブログ流出 | セキュリティ | Sec | 2 | 4 | 8 | マスキング/静的検査 | 2025-08-20 |
| R-17 | 監視/アラート誤作動・未発火 | 可観測性 | Obs | 2 | 4 | 8 | ルールCI/演習 | 2025-08-22 |
| R-18 | 最適化発注バグ（optimized_order_execution） | 実装 | Do | 2 | 5 | **10** | ゴールデン/契約テスト | 2025-08-21 |

---

## 3. 詳細レコード（Mitigation / KPI / Triggers）
> **凡例**: Appetite=許容レベル（超過は自動/手動アクション）、KPI/Trigger=監視ロジック（`Observability.md` 準拠）、Status=Open/Watching/Mitigated/Accepted/Closed。

### R-01 レジームシフト（相場構造変化）
- **Category**: 市場 / **Owner**: Risk(Noctus) / **Score**: 20 (**Red**) / **Appetite**: KPI悪化時は**Safemode必須**  
- **Mitigations**: `flags.risk_safemode=true` で Noctus 境界 0.5x、配分 7% 段階へダウン、A/Bで優位戦略へ切替  
- **KPI/Triggers**:  
  - `kpi_max_dd_pct` 7日移動 ≥ `risk_policy.max_drawdown_pct * 0.7`  
  - `kpi_win_rate` 7日移動 ≤ 0.48  
  - `risk_events_total{kind="LOSING_STREAK"}` 増分 > 0（即時）  
- **Runbooks**: §6（取引抑制）/ §8（ロールバック）  
- **Status**: Watching → **自動Safemode**まで設定済

### R-02 流動性低下/スリッページ急騰
- **Category**: 市場/実行 / **Owner**: Ops/Do / **Score**: 12 (**Orange**) / **Appetite**: p90 Slippage ≤ 0.3%  
- **Mitigations**: 分割発注/タイミング最適化、`max_slippage_pct` で自動中断、影響銘柄は一時除外  
- **KPI/Triggers**: `histogram_quantile(0.90, do_slippage_pct_bucket)` > 0.3 for 10m → **Pause検討**  
- **Runbooks**: §9.2 / **Do Contract**: §5.2

### R-03 ブローカー/API 障害
- **Category**: 外部依存 / **Owner**: Ops / **Score**: 15 (**Red**) / **Appetite**: 主要DAG停止時間 ≤ 30m  
- **Mitigations**: リトライ/指数バックオフ、代替経路、`global_trading_pause`、Webhook バッファリング  
- **KPI/Triggers**: `broker_api_errors_total / requests_total` > 0.01 for 10m、`broker_api_latency_seconds` p95 > 2s  
- **Runbooks**: §4/§9, API: `/ops/trading/pause`

### R-04 データ欠損/品質劣化（Plan）
- **Mitigations**: `max_fill_gap` 以内の F/BFill + 欠損フラグ、再取得DAG、データドリフト警告  
- **KPI/Triggers**: 欠損比率 > 1%/日、`KpiSummaryStale` 発火  
- **Links**: `Plan-Layer.md §6`, `Observability.md §10`

### R-06 Idempotency破れ/重複発注
- **Mitigations**: `Idempotency-Key` 必須、`audit_order.json` でハッシュ照合、重複検知で REJECT  
- **KPI/Triggers**: 同一 `correlation_id` で `orders_submitted_total` が 2 以上 → アラート  
- **Links**: `API.md §2`, `Do-Layer-Contract.md §8`

### R-07 リスク境界の誤設定/バイパス
- **Mitigations**: Config 二重承認（PR + King 承認）、Safemode 既定 ON（prod）、起動時に境界を**検証ログ**  
- **KPI/Triggers**: `risk_policy_validation_errors_total` > 0 → Pager、`flags.risk_safemode` が OFF で 24h 継続 → Warning  
- **Links**: `Config-Registry.md §8`, `Vision-Governance.md §5`

### R-08 モデルドリフト/過学習
- **Mitigations**: Walk-Forward、Optuna再学習、Shadow運用10日、段階導入7→30→100%  
- **KPI/Triggers**: `kpi_win_rate` 30日移動が 0.5 を割込、`sigma_mean` 異常（観測不足/過信）  
- **Links**: `ModelCard-Prometheus-PPO.md §10/11`, `Strategy-Lifecycle.md`

### R-09 スキーマドリフト（Plan→Do→Check）
- **Mitigations**: `jsonschema` CI、契約テスト（3パターン：FILLED/PARTIAL/REJECTED）、SemVer 運用  
- **KPI/Triggers**: スキーマ検証失敗数 > 0 → ビルド失敗  
- **Links**: `Do-Layer-Contract.md §12`, `API.md §12`

### R-10 Secrets漏えい/鍵期限切れ
- **Mitigations**: Vault/ENV 専用、90日ローテ、スキャン（静的/PR時）、監査  
- **KPI/Triggers**: 期限 ≤ 7日通知、失敗アクセスの増分 > 0  
- **Links**: `Security-And-Access.md`, `.env.sample`, `Runbooks.md §10`

### R-11 Airflow スケジューラ停止/滞留
- **Mitigations**: HealthCheck監視、再起動Runbook、Backfill指針、pool/並列度の上限設計  
- **KPI/Triggers**: `airflow_dag_runs_total{status="failed"}` 比率 > 5%（5m）、`pdca_check_flow` SLA miss  
- **Links**: `Airflow-DAGs.md §10/12`, `Runbooks.md §9.1`

（…他リスクは要約表のオーナーが担当し、同形式で追記）

---

## 4. アクションの自動化（Flags/Ops）
- **取引抑制**: `flags.global_trading_pause=true` → `/api/v1/ops/trading/pause`（GUI/CLI からも）  
- **Safemode**: `flags.risk_safemode=true`（Noctus 境界 0.5x）  
- **通知先**: Slack `#ops-alerts` / `#risk-duty`、PagerDuty（Severity 連動）  
- **ダッシュボード注釈**: 段階導入/インシデント/ロールバックを Grafana 注釈へ（`Observability.md §6`）

---

## 5. レビュー運用（Cadence）
- **Daily**: 重大アラート/新規リスクの**一次評価**（Ops+Risk）。  
- **Weekly**: Council で**Orange/Red**の進捗レビュー・Owner更新。  
- **Monthly**: 全件見直し、**Appetite/閾値**の適正化、`Release-Notes.md` への反映。  
- **Postmortem**: インシデント24h以内に草案 → 根本原因/再発防止 → 本表へ移す。

---

## 6. 追加テンプレ（New Risk Template）
```md
### R-XX {タイトル}
- **Category**: {市場/実行/データ/…} / **Owner**: {役割} / **Score**: L×I / **Appetite**: {定量 or ルール}
- **Mitigations**: {既存/恒久/短期の対策を箇条書き}
- **KPI/Triggers**: {PromQL/メトリクス/条件 or 手動判定}
- **Runbooks/Links**: {関連手順/設計/契約/ADR}
- **Status**: {Open/Watching/Mitigated/Accepted/Closed}
- **Next Review**: {YYYY-MM-DD}
```

---

## 7. 変更管理（Docs as Code）
- 重要な閾値変更は `Config-Registry.md` と**同一PR**で更新。  
- 恒久対策は `ADRs/` に Decision/Context/Consequences を記録。  
- 関連手順は `Runbooks.md`、監視は `Observability.md` を同期。

---

## 8. 変更履歴（Changelog）
- **2025-08-12**: 初版作成（スコア規約/トップリスク/自動化/テンプレ/運用）

