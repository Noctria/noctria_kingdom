# ✅ Testing & QA — Noctria Kingdom

**Version:** 1.1  
**Status:** Adopted  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の **PDCA/AI/実行/運用** をバグから守り、**安全・再現性・説明責任**を満たすためのテスト/QA 標準を定義する。  
> 参照：`../governance/Vision-Governance.md` / `../architecture/Architecture-Overview.md` / `../architecture/Plan-Layer.md` / `../operations/Runbooks.md` / `../operations/Config-Registry.md` / `../operations/Airflow-DAGs.md` / `../observability/Observability.md` / `../security/Security-And-Access.md` / `../apis/API.md` / `../apis/Do-Layer-Contract.md`

---

## 1. スコープ & ゴール
- スコープ：**コード**（Python/Configs/DAGs）、**契約**（JSON Schema/API）、**データ品質**、**モデル再現性**、**パフォーマンス/レジリエンス**、**監視/ルール**、**セキュリティ**。  
- ゴール：
  1) **Shift-left**：PR 時点で重大欠陥を検出（契約/スキーマ/静的解析）。  
  2) **Reproducibility**：学習・推論・評価は **固定シード**と**ゴールデン値**で再現可能。  
  3) **Safety**：`risk_policy` 超過なし、**監査/説明**の証跡が残る。  
  4) **Quality Gates**：数値しきい値で**自動合否**を判定（本書 §5・§15）。

---

## 2. テスト・ピラミッド（全体像）
```mermaid
flowchart TB
  U["Unit Tests<br/>関数/小モジュール"] --> C["Contract Tests<br/>JSON Schema / API"]
  C --> I["Integration Tests<br/>Adapter / Tasks / DB"]
  I --> E["E2E (PDCA)<br/>最小本流 + 監査/説明"]
  E --> P["Perf / Resilience<br/>負荷 / スパイク / 故障注入"]
  U -.-> DQ["Data Quality<br/>欠損 / 外れ / 整合"]
  E -.-> OBS["Observability Rules<br/>Alert / Loki / PromQL"]
```

---

## 3. テスト種別 & 最低基準

### 3.1 Unit（pytest）
- 目的：純粋ロジック（特徴量、ロット計算、日付・端数・丸め）。  
- 基準：**カバレッジ 80%**（ビジネスロジック領域）。  
```bash
pytest -q tests/unit
```

### 3.2 Contract（JSON Schema / API）
- 対象：`order_request/exec_result/risk_event/kpi_summary/risk_policy`（`docs/schemas/*.schema.json`）。  
- 基準：**スキーマ適合 100%**＋**後方互換チェック**（必須プロパティ削除は Fail）。  
```bash
python -m jsonschema -i samples/exec_result_ok.json docs/schemas/exec_result.schema.json
pytest -q tests/contract
```

### 3.3 Integration（Adapter/Tasks/DB/Files）
- 対象：`broker_adapter.py`, `order_execution.py`, Plan/Check タスク。  
- 基準：FILLED / PARTIAL / REJECTED の **3 ケース再現**、丸め・桁・TickSize 合致（`Do-Layer-Contract.md §5.3`）。  
```bash
pytest -q tests/integration -m "not slow"
```

### 3.4 E2E（最小本流・監査/説明つき）
- 対象：`pdca_plan_workflow → do_layer_flow → pdca_check_flow → pdca_act_flow` のスモーク。  
- 合格：`audit_order.json` 生成、`kpi_summary.json` 更新、Hermes 説明が空でない。  
```bash
pytest -q tests/e2e --maxfail=1
```

### 3.5 Data Quality（Plan）
- 項目：**欠損/外れ/時間整合/祝日**。  
- 基準：欠損比 ≤ 1%/日、重複バー=0、時刻整合 OK、統計（平均・分散）安定。  
```bash
pytest -q tests/data_quality
```

### 3.6 プロパティベース（Hypothesis）
- 例：ロットは `qty>=0` かつ **境界越えなし**、極端入力でも NaN を出さない。  
```python
from hypothesis import given, strategies as st
@given(st.floats(min_value=-1, max_value=1))
def test_lot_never_exceeds_policy(sig):
    qty = to_lot(sig, policy)
    assert 0.0 <= qty <= policy.max_position_qty
```

### 3.7 再現性（ゴールデン/シード固定）
- 小区間で学習・推論・評価 → **出力ハッシュ一致**（Git SHA/seed/依存と突合）。  
```bash
pytest -q tests/repro  # /data/golden/** と比較
```

### 3.8 パフォーマンス / レジリエンス
- 目的：Do 層 p95 < 500ms、障害時の**安全停止**。  
- ツール：`k6`/`locust`、故障注入（遅延/接続切断/429）。  
```bash
k6 run tests/perf/do_orders_p95.js
pytest -q tests/resilience -m fault_injection
```

### 3.9 セキュリティ
- SAST/依存脆弱性/シークレットスキャン（PII/Secrets ログ禁止も検査）。  
```bash
bandit -q -r src
pip-audit -r requirements.txt
gitleaks detect --no-banner
```

### 3.10 監視・ルール（Observability）
- Prometheus Rules / Loki クエリの静的検証 & リハーサル。  
```bash
promtool check rules deploy/alerts/noctria.rules.yml
pytest -q tests/observability
```

### 3.11 API 併走性 & Idempotency
- 同一 `Idempotency-Key` の再送 → **重複実行なし**、24h 保持の検証。  
- PATCH は `If-Match` 必須（ETag 競合 412 を期待）。  
```bash
pytest -q tests/api_idempotency
```

### 3.12 Streaming / Webhook
- SSE：`Last-Event-ID` 再接続で欠落イベントが補完される。  
- Webhook：HMAC 署名検証（時刻乖離 ±5分）で Fail/Pass を確認。  
```bash
pytest -q tests/streaming_webhooks
```

---

## 4. 環境マトリクス & ゲーティング
| 種別 | dev | stg | prod |
|---|---:|---:|---:|
| Lint / SAST / Contract | ✅ | ✅ | ✅ |
| Unit / Integration | ✅ | ✅ | ✅ |
| E2E（シャドー/低ロット） | ⭕ | ✅ | 🔸（カナリアのみ） |
| Perf / Resilience | ⭕ | ✅ | 🔸（事前掲示） |
| Observability Rehearsal | ✅ | ✅ | ✅ |
| Security (gitleaks/pip-audit) | ✅ | ✅ | ✅ |

> 🔸=本番は**事前告知＆時間帯制限**。昇格は `Strategy-Lifecycle.md` の **G2/G3/G4** を満たすこと。

---

## 5. CI/CD（推奨パイプライン & ゲート）
```mermaid
flowchart LR
  A["PR Open"] --> L["Lint / Format / SAST"]
  L --> S["Schema / Contract"]
  S --> U["Unit"]
  U --> I["Integration (Docker test stack)"]
  I --> B["Build images + SBOM + Vuln Scan"]
  B --> E["E2E (stg, shadow/low-lot)"]
  E --> G["Gates: KPI / Alerts / SLA"]
  G -->|pass| D["Deploy stg"]
  D --> C["Canary prod (7%)"]
  C --> R["Promote 30% → 100%"]
  G -->|fail| X["Block + Report"]
```

**ゲート条件（例）**
- `do_order_latency_seconds` **p95 ≤ 0.5s**（stg）  
- `do_slippage_pct` **p90 ≤ 0.3%**（stg, 10m）  
- `kpi_win_rate`（7d）≥ **0.50**、`kpi_max_dd_pct`（7d）≤ **8%**  
- **重大アラート 0 件**（`Observability.md §5`）  
- **契約テスト 100%**、**Secrets 漏えい 0**（gitleaks）  
- **ゴールデン差分 0**（許容 ε 以内）

**PR ラベルで追加ゲート**  
- `breaking-contract`：後方互換テスト強化 + 互換レポート必須  
- `perf-sensitive`：Perf/Resilience を必須に昇格  
- `security-impact`：SAST/依存監査の厳格モード

---

## 6. ローカル実行（開発者向け）
```bash
# 事前
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# まとめ実行
make test          # lint + unit + contract
make test-full     # + integration + e2e (ローカル最小)
make schemas-check # JSON Schema 静的検証

# Docker テストスタック（任意）
docker compose -f deploy/test/docker-compose.yml up -d
pytest -q tests/integration
```

**Makefile（抜粋）**
```make
test: lint schemas unit
test-full: test integration e2e
lint:
	ruff check src tests
	black --check src tests
schemas:
	python tools/validate_schemas.py
unit:
	pytest -q tests/unit
integration:
	docker compose -f deploy/test/docker-compose.yml up -d
	pytest -q tests/integration
e2e:
	pytest -q tests/e2e -m "smoke"
```

---

## 7. フィクスチャ & テストデータ
- **ディレクトリ**：`tests/fixtures/{plan,do,check,models}/**`  
- **ゴールデン**：`tests/golden/**`（出力ハッシュ用）  
- **合成データ**：極端値/欠損/レート制限を再現した疑似ブローカーを同梱  
- **シード**：`[1337, 1729, 31415]` を基本（`ModelCard-Prometheus-PPO.md` と整合）  
- **データ責務**：PII/Secrets を含めない（`Security-And-Access.md`）

---

## 8. Airflow QA（必須チェック）
- **DAG Import**：`airflow dags list` がゼロエラー  
- **SLA**：`airflow_dag_sla_miss_total` が閾値以下  
- **Dry Runs**：代表タスク `--dry-run` が完了  
- **Backfill 小区間**：UTC 1 日で成功、**idempotent**  
```bash
airflow dags list
airflow tasks test pdca_plan_workflow generate_features 2025-08-12
airflow dags backfill -s 2025-08-11 -e 2025-08-12 pdca_check_flow
```

---

## 9. Do-Layer 契約テスト（3パターン最低）
```json
// FILLED（期待）
{"status":"FILLED","filled_qty":0.5,"avg_price":59001.0,"fees":0.12}
```
```json
// PARTIAL（中断でも filled_qty>0）
{"status":"CANCELLED","filled_qty":0.3,"avg_price":59010.0}
```
```json
// REJECTED（越境/抑制）
{"error":{"code":"RISK_BOUNDARY_EXCEEDED"}}
```
- スキーマ適合 + 丸め/桁 + `audit_order.json` 生成の有無で判定（`Do-Layer-Contract.md`）。  
- **Idempotency**：同一 `Idempotency-Key` 再送で**重複なし**（24h 保持）。

---

## 10. KPI パイプライン QA（Check/Act）
- **入力**：`/data/execution_logs/*.json`（疑似データ）  
- **出力**：`kpi_summary.json` の **スキーマ/値域/更新時刻** を検証。  
- **Hermes**：説明テキストが**空/不整合**でない。  
- **Schema Version**：`kpi_summary.schema.json` に `schema_version` を付与・照合。

---

## 11. モデル QA（Prometheus/Veritas）
- **推論安定性**：同一入力 → **同一出力**（許容 ε）  
- **学習再現**：小区間学習 → 指標 ±Δ（閾値 3%）  
- **過学習**：Train/Test 乖離が**設定範囲内**  
- **安全**：アクション→ロット変換で **境界越えなし**（Noctus シミュレーション）  
- **ドリフト**：`action_mean/std`, `turnover`, `hit_rate` 監視と**再学習トリガ条件**を定義

---

## 12. リリース・ゲーティング & 段階導入
- **カナリア**：`Strategy-Lifecycle.md §4.4`（7%→30%→100%、Safemode ON）。  
- **昇格**：§5 のゲートを **連続営業日**クリア、重大アラート 0。  
- **ロールバック**：`Runbooks.md §8`（`risk_event` で即時停止検討）。

---

## 13. バグ管理 & 優先度
| Severity | 定義 | 例 | 目標応答 |
|---|---|---|---|
| S1 | 安全/財務に重大 | 連続発注/境界無視/監査欠落 | 即時対応・抑制ON |
| S2 | 本番影響大 | p95>0.5s 持続、DAG停止 | 当日内修正/回避 |
| S3 | 影響中 | 一部戦略のみ劣化 | 次リリース |
| S4 | 低 | UI/文言/軽微ログ | バックログ |

**Flaky 対応**：再現性なしを 2 回検出→**quarantine** ラベル付与、専用ジョブで隔離テスト。  
**再試行方針**：ネットワーク系のみ指数バックオフ、ビジネス NG は**再試行禁止**。

---

## 14. テンプレ & 例

### 14.1 テスト計画テンプレ
```md
# Test Plan — {Feature/Change}
- 背景/目的:
- 影響範囲:
- テスト対象/除外:
- テスト種別: Unit/Contract/Integration/E2E/Perf/Sec/Obs
- データ/フィクスチャ:
- 合格基準（メトリクス/しきい値）:
- リスク/ロールバック:
- 実施者/レビュー/承認:
```

### 14.2 pytest.ini（例）
```ini
[pytest]
addopts = -q -ra --maxfail=1
testpaths = tests
markers =
    slow: 長時間
    fault_injection: 故障注入
    smoke: スモーク
    quarantine: 不安定テスト
```

### 14.3 pre-commit（抜粋）
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks: [{id: black}]
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.5.0
    hooks: [{id: ruff}]
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks: [{id: gitleaks}]
```

---

## 15. カバレッジ & 品質基準（Quality Gates）
- **ライン**：総合 75% 以上、コア（Plan/Do/Noctus）**80% 以上**。  
- **Lint**：`ruff/black` ゼロエラー。`mypy --strict` 合格（型エラー 0）。  
- **契約**：スキーマ 100% 準拠、**後方互換 OK**。  
- **Perf**：Do 層 p95 < **0.5s**（stg）。  
- **セキュリティ**：`gitleaks` 0 件、`pip-audit` High 以上 0 件。  
- **再現性**：ゴールデン差分 0（許容 ε は機能別に明記）。  

> いずれか 1 つでも **Fail → デプロイブロック**。例外は `ADR` による承認が必要。

---

## 16. 変更管理（Docs as Code）
- 仕様変更は **同一PR**で本書と関連ドキュメント（`API / Do-Layer-Contract / Runbooks / Config-Registry / Observability`）を更新。  
- 重要な QA 変更は `ADRs/` に記録（Decision / Rollout / Consequences）。

---

## 17. 既知の制約 / TODO
- 本番での**故障注入**は限定的（時間帯制約・影響最小化）。  
- 取引所レート制限の**動的追随**（自動検出→テストのしきい値更新）を強化予定。

---

## 18. 変更履歴（Changelog）
- **2025-08-12**: v1.1 追記（Idempotency/If-Match/SSE/Webhook、Flaky 対応、ゲート拡充、Mermaid 互換化）
- **2025-08-12**: v1.0 初版作成（ピラミッド/基準/CI/Airflow/Do契約/モデル/監視/ゲーティング）
