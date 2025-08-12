<!-- ================================================================== -->
<!-- FILE: docs/howto/README.md -->
<!-- ================================================================== -->
# 🧩 Howto Index — Noctria Kingdom

**Document Set Version:** 1.0  
**Status:** Adopted  
**Last Updated:** 2025-08-12 (JST)

> 本ディレクトリには、運用・検証・緊急対応の **手順（Howto）テンプレ** を収録します。  
> 変更は **Docs-as-Code**（関連ドキュメントと同一PR）で行い、`Release-Notes.md` に反映します。

## 目次（テンプレ）
- `howto-backfill.md` — Airflow バックフィル手順
- `howto-airflow-debug.md` — Airflow タスクのデバッグ/再実行
- `howto-shadow-trading.md` — シャドー運用の開始/停止
- `howto-start-canary.md` — 段階導入（7%→30%→100%）
- `howto-rollback.md` — ロールバック/停止/復帰
- `howto-trading-pause.md` — 全局取引抑制（Pause/Resume）
- `howto-config-change.md` — Config/Flags の安全な変更
- `howto-update-risk-policy.md` — リスク境界の改訂（Two-Person）
- `howto-run-local-tests.md` — ローカルでのテスト/スモーク
- `howto-collect-evidence.md` — 事故証跡の収集と添付
- `howto-add-alert-rule.md` — アラートルールの追加/検証
- `howto-rotate-secrets.md` — Secrets ローテーション

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-backfill.md -->
<!-- ================================================================== -->
# ⏪ Howto: Airflow バックフィル

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 目的
欠損/遅延データや一時失敗を **安全に** バックフィルし、再現性を保って PDCA を復旧する。

## 前提
- 影響範囲を把握（対象 DAG/期間/下流アーティファクト）。  
- `Security-And-Access.md` に基づき **Ops 権限**を保有。  
- 関連：`Runbooks.md §12`, `Airflow-DAGs.md §10`, `Plan-Layer.md §6`

## セーフティチェック
- 本番負荷：I/O 飽和を防ぐため **pools/並列度** を制限。  
- Secrets/Config の時系列整合（当時の `{env}.yml` を再現）。  
- 監査：`correlation_id` を固定してログ/結果をトレース可能に。

## 手順
```bash
# 1) 影響確認
airflow dags list-runs -d pdca_plan_workflow --no-backfill

# 2) プール/並列度の設定（必要に応じ）
airflow pools set backfill_pool 2 "Backfill limited pool"

# 3) Dry-run（代表タスク）
airflow tasks test pdca_plan_workflow generate_features 2025-08-11

# 4) 本実行（UTCで期間指定）
airflow dags backfill -s 2025-08-11 -e 2025-08-12 -p backfill_pool pdca_plan_workflow

# 5) 出力検証（ハッシュ/スキーマ）
python tools/validate_artifacts.py --from 2025-08-11 --to 2025-08-12
```

## 検証
- `kpi_summary_timestamp_seconds` が更新、`Observability` にアラート無し。  
- `features_dict.json` / `kpi_stats.json` のスキーマOK、欠損フラグ/比率が許容内。

## ロールバック
- バックフィル産物を隔離パスへ退避、直前スナップへ戻す。  
- 影響期間の DAG 実行を **skip** して正常化。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-airflow-debug.md -->
<!-- ================================================================== -->
# 🧰 Howto: Airflow タスクのデバッグ/再実行

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 目的
失敗タスクの **原因特定** と **最小影響の再実行**。

## 手順（最小セット）
```bash
# ログ参照
airflow tasks logs pdca_plan_workflow generate_features 2025-08-12

# 依存表示
airflow tasks list pdca_plan_workflow --tree

# 単発テスト（副作用なし）
airflow tasks test pdca_plan_workflow compute_statistics 2025-08-12

# 再実行（失敗分のみ）
airflow tasks clear -s 2025-08-12 -e 2025-08-12 -t compute_statistics -d pdca_plan_workflow
```

## ポイント
- **Idempotency** を確認（再実行で重複書き込みしない）。  
- Secrets は **Connections/ENV** から注入されているか確認。  
- 失敗原因は **Logs/Traces** と **Config差分** で突合。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-shadow-trading.md -->
<!-- ================================================================== -->
# 🕶️ Howto: シャドー運用の開始/停止

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 目的
本番入力に対し **発注せず** KPI/監査のみを記録する “shadow” を設定。

## 手順
1. `Config-Registry.md` の `flags.shadow=true`（stg）を設定。  
2. 戦略の API 提案に `meta.shadow=true` を付与。  
3. `Observability` ダッシュで `shadow` タグが付与されていることを確認。  
4. 10 営業日 or 200 取引を目安に評価。  

## 停止
- `flags.shadow=false` に戻し、通常運用へ。  
- 期間中の `audit_order.json` を保存し、`Strategy-Lifecycle.md` に所見を記載。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-start-canary.md -->
<!-- ================================================================== -->
# 🐤 Howto: 段階導入（カナリア 7%→30%→100%）

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 前提
- G0〜G3 のゲートをクリア（`Strategy-Lifecycle.md §4`）。  
- `risk_safemode=true`（Noctus 境界 0.5x）。

## 手順
```bash
# 1) 採用開始（API）
curl -X POST /api/v1/act/adopt -d '{
  "name":"Prometheus-PPO","version":"1.2.0",
  "plan":{"stages":[0.07,0.3,1.0],"days_per_stage":3}
}'

# 2) Grafana 注釈を投入（任意）
# 3) 観測：latency p95 / slippage p90 / KPI の推移
```

## 昇格/停止基準
- 昇格：前段の 3 営業日、**重大アラート0**、KPIレンジ内。  
- 停止：`SlippageSpike` / `LosingStreak` 発火、MaxDD 閾値 70% 到達。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-rollback.md -->
<!-- ================================================================== -->
# 🔁 Howto: ロールバック（停止→復帰）

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## ケース
- KPI 劣化/連敗/スリッページ急騰、インシデント時。

## 即時手順
1) `global_trading_pause=true`（必要時）。  
2) **配分を直前安定版へ** 戻す（7% 段階まで減衰）。  
3) Runbooks のチェックリストに従い復旧→Safemode 維持で低ロット再開。  

## 検証
- `exec_result` 正常化、アラート消失、KPI 安定。  
- `Incident-Postmortems.md` を 24h 以内に起票。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-trading-pause.md -->
<!-- ================================================================== -->
# 🧯 Howto: 全局取引抑制（Pause/Resume）

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 目的
緊急時に **全ての実発注** を一時停止し、状況安定後に段階再開。

## 手順
```bash
# 抑制ON
curl -X PATCH /api/v1/config/flags -d '{"flags":{"global_trading_pause":true}}'
# 抑制OFF
curl -X PATCH /api/v1/config/flags -d '{"flags":{"global_trading_pause":false}}'
```

## 注意
- 抑制中も **シャドー/評価** は実行可。  
- 再開は **Safemode ON + 低ロット** から。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-config-change.md -->
<!-- ================================================================== -->
# 🧩 Howto: Config/Flags の安全な変更

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 原則
- SoT：`Config-Registry.md`（defaults → env → flags → secrets）。  
- **Two-Person Rule**（重要キーはレビュー+King 承認）。

## 手順
1. 変更案を PR（差分を明示、影響/ロールバック/検証手順を記述）。  
2. stg で **Dry-run + スモーク**、Observability で逸脱なしを確認。  
3. prod へ適用、注釈を追加、`Release-Notes.md` に記録。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-update-risk-policy.md -->
<!-- ================================================================== -->
# 🛡 Howto: リスク境界（risk_policy）改訂

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 対象
`max_drawdown_pct`, `stop_loss_pct`, `take_profit_pct`, `max_position_qty`, `losing_streak_threshold`, `max_slippage_pct` など。

## 手順（Two-Person + King）
1. 現状KPI/アラートの根拠を整理（`Risk-Register.md` と整合）。  
2. PR：`{env}.yml` 差分 + 根拠、AB影響、ロールバック案。  
3. stg シャドーで10営業日観測。  
4. 承認後に prod へ、`Strategy-Lifecycle.md` と `Release-Notes.md` を更新。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-run-local-tests.md -->
<!-- ================================================================== -->
# 🧪 Howto: ローカルでのテスト/スモーク

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## セットアップ
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
```

## 実行
```bash
make test          # lint + unit + schema
make test-full     # + integration + e2e (最小)
pytest -q tests/e2e -m smoke
```

## 合格基準
- 契約スキーマ 100% 準拠、Do 層 3パターン（FILLED/PARTIAL/REJECTED）をカバー。  
- ゴールデン差分なし、主要メトリクスの p95/p90 が基準内。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-collect-evidence.md -->
<!-- ================================================================== -->
# 📦 Howto: 事故証跡の収集と添付

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 目的
ポストモーテム用に **ログ/メトリクス/監査/設定差分** をワンパッケージ化。

## 手順
```bash
python tools/collect_evidence.py --from 2025-08-12T06:00Z --to 2025-08-12T09:00Z \
  --out evidence_20250812_0600_0900.zip
```
- 含めるもの：構造化ログ、Prometheus CSV、`audit_order.json` 一式、`{env}.yml` 差分、ダッシュボード画像。  
- `incidents/PM-YYYYMMDD-*.md` に添付リンクを記載。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-add-alert-rule.md -->
<!-- ================================================================== -->
# 🔔 Howto: アラートルールの追加/検証

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 目的
誤検知を抑えつつ **本質的逸脱** を検知する Prometheus ルールを追加。

## 手順
1. 目的とメトリクスを定義（観測対象としきい値）。  
2. ルールを追加：`deploy/alerts/noctria.rules.yml`。  
3. 静的検証：`promtool check rules`。  
4. リハーサル：stg で負荷/異常の疑似発生 → アラート発火/収束を確認。  
5. `Observability.md` と `Runbooks.md` を更新。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-rotate-secrets.md -->
<!-- ================================================================== -->
# 🔑 Howto: Secrets ローテーション

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-12 (JST)

## 原則
- Secrets は **Vault/ENV** のみ、Airflow Variables に保存しない。  
- ローテ間隔は **90日**、期限切れ 7日前に通知。

## 手順
1. 新しいキーを発行（ブローカー/IdP）。  
2. stg へ注入 → スモーク合格を確認。  
3. メンテナンス時間帯に prod を切替。  
4. 旧キー revoke、監査に記録、`Security-And-Access.md` を更新。

---

## 変更履歴（Changelog for Howto Set）
- **2025-08-12**: 初版テンプレ群を追加（Backfill/Airflow Debug/Shadow/Canary/Rollback/Pause/Config/Risk/Local Tests/Evidence/Alert/Secrets）

