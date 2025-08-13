<!-- ================================================================== -->
<!-- FILE: docs/howto/README.md -->
<!-- ================================================================== -->
# 🧩 Howto Index — Noctria Kingdom

**Document Set Version:** 1.1  
**Status:** Adopted  
**Last Updated:** 2025-08-14 (JST)

> 本ディレクトリには、運用・検証・緊急対応の **手順（Howto）テンプレ** を収録します。  
> 変更は **Docs-as-Code**（関連ドキュメントと同一PR）で行い、`Release-Notes.md` に反映します。

## 目次（テンプレ）
- `howto-backfill.md` — Airflow バックフィル手順
- `howto-airflow-debug.md` — Airflow タスクのデバッグ/再実行
- `howto-shadow-trading.md` — シャドー運用の開始/停止（**flags.dry_run** と **meta.shadow** を使用）
- `howto-start-canary.md` — 段階導入（7%→30%→100%）
- `howto-rollback.md` — ロールバック/停止/復帰
- `howto-trading-pause.md` — 全局取引抑制（Pause/Resume）
- `howto-config-change.md` — Config/Flags の安全な変更
- `howto-update-risk-policy.md` — リスク境界の改訂（Two-Person）
- `howto-run-local-tests.md` — ローカルでのテスト/スモーク
- `howto-collect-evidence.md` — 事故証跡の収集と添付
- `howto-add-alert-rule.md` — アラートルールの追加/検証
- `howto-rotate-secrets.md` — Secrets ローテーション
- `howto-gui-systemd-env.md` — **GUI(systemd) 環境変数 読み込み不良の復旧手順（$NOCTRIA_GUI_PORT など）**
- `howto-refresh-observability.md` — 観測マテビュー/タイムラインの再計算 & キャッシュ更新

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-backfill.md -->
<!-- ================================================================== -->
# ⏪ Howto: Airflow バックフィル

**Version:** 1.1 / **Status:** Adopted / **Last Updated:** 2025-08-14 (JST)

## 目的
欠損/遅延データや一時失敗を **安全に** バックフィルし、再現性を保って PDCA を復旧する。

## 前提
- 影響範囲を把握（対象 DAG/期間/下流アーティファクト）。  
- `Security-And-Access.md` に基づき **Ops 権限**を保有。  
- 関連：`Runbooks.md §12`, `Airflow-DAGs.md §10`, `Plan-Layer.md §6`

## セーフティチェック
- 本番負荷：I/O 飽和を防ぐため **pools/並列度** を制限。  
- Secrets/Config の時系列整合（当時の `{env}.yml` を再現）。  
- 監査：`trace_id` を固定してログ/結果をトレース可能に。

## 手順
```bash
# 1) 影響確認（失敗ランの把握）
airflow dags list-runs -d pdca_plan_workflow --state failed

# 2) プール/並列度の設定（必要に応じ）
airflow pools set backfill_pool 2 "Backfill limited pool"

# 3) Dry-run（代表タスク）
airflow tasks test pdca_plan_workflow generate_features 2025-08-11

# 4) 本実行（UTCで期間指定、プールを明示）
airflow dags backfill -s 2025-08-11 -e 2025-08-12 --pool backfill_pool pdca_plan_workflow

# 5) 出力検証（ハッシュ/スキーマ）
python tools/validate_artifacts.py --from 2025-08-11 --to 2025-08-12
```

## 検証
- `kpi_summary_timestamp_seconds` が更新、`Observability` にアラート無し。  
- `features_dict.json` / `kpi_stats.json` のスキーマOK、欠損率が許容内。

## ロールバック
- バックフィル産物を隔離パスへ退避、直前スナップへ戻す。  
- 影響期間の DAG 実行を **skip** して正常化。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-airflow-debug.md -->
<!-- ================================================================== -->
# 🧰 Howto: Airflow タスクのデバッグ/再実行

**Version:** 1.1 / **Status:** Adopted / **Last Updated:** 2025-08-14 (JST)

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

# 再実行（依存下流も含めてクリア）
airflow tasks clear --downstream -s 2025-08-12 -e 2025-08-12 -t compute_statistics pdca_plan_workflow
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

**Version:** 1.1 / **Status:** Adopted / **Last Updated:** 2025-08-14 (JST)

## 目的
本番入力に対し **発注せず** KPI/監査のみを記録する “shadow” を設定。

## 手順
1. stg 環境で `flags.dry_run=true`（発注をログのみに）を設定。  
2. 戦略の提案/出力に `meta.shadow=true` を付与（Do-Layer Contract の拡張フィールド）。  
3. `Observability` ダッシュで `shadow` タグが付与されていることを確認。  
4. 10 営業日 or 200 取引を目安に評価。

## 停止
- `flags.dry_run=false` に戻し、通常運用へ。  
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
curl -X POST http://localhost:8001/api/v1/act/adopt -H 'Content-Type: application/json' -d '{
  "name":"Prometheus-PPO","version":"1.2.0",
  "plan":{"stages":[0.07,0.3,1.0],"days_per_stage":3}
}'

# 2) 注釈（任意）
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
curl -X PATCH http://localhost:8001/api/v1/config/flags -H 'Content-Type: application/json' -d '{"flags":{"global_trading_pause":true}}'
# 抑制OFF
curl -X PATCH http://localhost:8001/api/v1/config/flags -H 'Content-Type: application/json' -d '{"flags":{"global_trading_pause":false}}'
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

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-gui-systemd-env.md -->
<!-- ================================================================== -->
# 🛠️ Howto: GUI(systemd) の環境変数が反映されない時の復旧

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-14 (JST)

> 症状例：Gunicorn 起動時に  
> `Error: '$NOCTRIA_GUI_PORT' is not a valid port number.`  
> がログに出て GUI が落ちる / 再起動を繰り返す。

## 主因（よくある）
- `/etc/default/noctria-gui` の **改行が CRLF**（^M が付く）  
- unit の `ExecStart` が **/bin/sh -lc になっていない**（環境変数が展開されない）  
- `EnvironmentFiles=` の **パス/権限**が不正  
- 値に **引用符** や 余計なスペースが入っている

## 確認
```bash
# 環境ファイル/環境/ExecStart を確認
sudo systemctl show -p EnvironmentFiles -p Environment -p ExecStart noctria_gui

# ポートで LISTEN しているか（fallback: ログ）
ss -ltnp | grep ":${NOCTRIA_GUI_PORT:-8001}" || sudo journalctl -u noctria_gui -n 80 --no-pager

# CRLF の有無（末尾に ^M があれば CRLF）
sudo sed -n 'l' /etc/default/noctria-gui
```

## 復旧手順
```bash
# 1) CRLF→LF（必要時）
sudo apt-get update && sudo apt-get install -y dos2unix
sudo dos2unix /etc/default/noctria-gui

# 2) 内容を2行だけにする（引用符/先頭空白なし）
sudo tee /etc/default/noctria-gui >/dev/null <<'EOF'
NOCTRIA_OBS_PG_DSN=postgresql://noctria:noctria@127.0.0.1:55432/noctria_db
NOCTRIA_GUI_PORT=8001
EOF

# 3) 権限/所有
sudo chown root:root /etc/default/noctria-gui
sudo chmod 0644 /etc/default/noctria-gui

# 4) unit の ExecStart を /bin/sh -lc 経由に（環境展開のため）
#   例: /etc/systemd/system/noctria_gui.service
# [Service]
# EnvironmentFiles=/etc/default/noctria-gui
# Environment=PYTHONPATH=/mnt/d/noctria_kingdom
# Environment=PYTHONUNBUFFERED=1
# ExecStart=/bin/sh -lc 'exec /mnt/d/noctria_kingdom/venv_gui/bin/gunicorn \
#   --workers 4 \
#   --worker-class uvicorn.workers.UvicornWorker \
#   -b 0.0.0.0:${NOCTRIA_GUI_PORT} \
#   noctria_gui.main:app'

# 5) 反映
sudo systemctl daemon-reload
sudo systemctl restart noctria_gui

# 6) 再確認
sudo systemctl show -p EnvironmentFiles -p Environment -p ExecStart noctria_gui
ss -ltnp | grep ":${NOCTRIA_GUI_PORT:-8001}"
curl -sS http://127.0.0.1:${NOCTRIA_GUI_PORT:-8001}/healthz
```

## 補足
- `EnvironmentFiles=` は **KEY=VALUE** のみ（`export` や `"..."` は不要）。  
- 変数は **/bin/sh -lc** 経由で起動しないと `-b 0.0.0.0:$VAR` の展開に失敗する場合あり。  
- それでも展開されない場合、`-b` に **固定ポート**を直書きして原因を切り分ける。

---

<!-- ================================================================== -->
<!-- FILE: docs/howto/howto-refresh-observability.md -->
<!-- ================================================================== -->
# 📈 Howto: 観測マテビュー/タイムラインの再計算 & キャッシュ更新

**Version:** 1.0 / **Status:** Adopted / **Last Updated:** 2025-08-14 (JST)

## 目的
`obs_*` テーブルの更新遅延や部分欠損時に、GUI の **PDCA Timeline** や **Latency 日次** を再計算/再読込する。

## 手順（GUI/API）
```bash
# Timeline / Latency のマテビュー/集計を再計算
curl -X POST http://localhost:8001/pdca/observability/refresh

# 直後に画面を再読込して可視化を確認
```

## 期待結果
- `obs_trace_timeline` / `obs_trace_latency` / `obs_latency_daily` が再計算され、最新の `trace_id` 連鎖が GUI に反映。  
- 失敗時は 5xx とエラーログが出力されるため、`journalctl -u noctria_gui` を参照。

---

## 変更履歴（Changelog for Howto Set）
- **2025-08-14**: v1.1  
  - **GUI(systemd) 環境変数の復旧**（CRLF / ExecStart / perms / healthz）を追加。  
  - **Observability リフレッシュ**手順を追加。  
  - Airflow CLI の例を最新化（`--downstream`/`--pool`/`--state`）。  
  - シャドー手順を `flags.dry_run + meta.shadow` に統一（Config と整合）。  
- **2025-08-12**: v1.0 初版テンプレ群（Backfill/Airflow Debug/Shadow/Canary/Rollback/Pause/Config/Risk/Local Tests/Evidence/Alert/Secrets）
