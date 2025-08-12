# ✅ Testing & QA — Noctria Kingdom

**Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria の **PDCA/AI/実行/運用** をバグから守り、**安全・再現性・説明責任**を満たすためのテスト/QA 標準を定義する。  
> 参照：`../governance/Vision-Governance.md` / `../architecture/Architecture-Overview.md` / `../architecture/Plan-Layer.md` / `../operations/Runbooks.md` / `../operations/Config-Registry.md` / `../operations/Airflow-DAGs.md` / `../observability/Observability.md` / `../security/Security-And-Access.md` / `../apis/API.md` / `../apis/Do-Layer-Contract.md`

---

## 1. スコープ & ゴール
- スコープ：**コード**（Python/Configs/DAGs）、**契約**（JSON Schema/API）、**データ品質**、**モデル再現性**、**パフォーマンス/レジリエンス**、**監視/ルール**。  
- ゴール：
  1) **shift-left**：PR 時点で重大欠陥を検出（契約/スキーマ/静的解析）。  
  2) **再現性**：学習・推論・評価は **固定シード**と**ゴールデン値**で再現可能。  
  3) **安全性**：`risk_policy` 超過なし、**監査/説明**の証跡を残す。  

---

## 2. テスト・ピラミッド（全体像）
```mermaid
flowchart TB
  U[Unit Tests<br/>関数/小モジュール] --> C[Contract Tests<br/>JSON Schema / API]
  C --> I[Integration Tests<br/>Adapter/Tasks/DB]
  I --> E[E2E (PDCA)<br/>最小本流 + 監査/説明]
  E --> P[Perf/Resilience<br/>負荷/スパイク/故障注入]
  U -.-> DQ[Data Quality<br/>欠損/外れ/整合]
  E -.-> OBS[Observability Rules<br/>Alert/Loki/PromQL]
```

---

## 3. テスト種別 & 最低基準

### 3.1 Unit（pytest）
- 目的：関数/クラスの**純粋ロジック**検証（例：特徴量関数、ロット計算）。  
- 最低基準：**カバレッジ 80%**（ビジネスロジック領域）。  
- 実行例：
```bash
pytest -q tests/unit
```

### 3.2 Contract（JSON Schema / API）
- 対象：`order_request/exec_result/risk_event/kpi_summary/risk_policy` など `docs/schemas/*.schema.json`。  
- 最低基準：**全スキーマ適合 100%**。  
```bash
python -m jsonschema -i samples/exec_result_ok.json docs/schemas/exec_result.schema.json
pytest -q tests/contract
```

### 3.3 Integration（Adapter/Tasks/DB/Files）
- 対象：`broker_adapter.py`, `order_execution.py`, Plan/Check タスク。  
- 最低基準：FILLED/PARTIAL/REJECTED の 3 ケースを**必ず**再現。  
```bash
pytest -q tests/integration -m "not slow"
```

### 3.4 E2E（最小本流・監査/説明つき）
- 対象：`pdca_plan_workflow → do_layer_flow → pdca_check_flow → pdca_act_flow` の**スモーク**。  
- 基準：成功、`audit_order.json` 生成、`kpi_summary.json` 更新、Hermes説明の生成を確認。  
```bash
pytest -q tests/e2e --maxfail=1
```

### 3.5 Data Quality（Plan）
- 目的：**欠損/外れ/時間整合/祝日**の自動チェック。  
- 基準：欠損比率 ≤ 1%/日、重複バー=0、時刻整合=OK。  
```bash
pytest -q tests/data_quality
```

### 3.6 プロパティベース（Hypothesis）
- 例：ロット計算は `qty>=0` かつ **境界を越えない**、特徴量は **ロバスト**（極端入力でも NaN を出さない）。  
```python
from hypothesis import given, strategies as st
@given(st.floats(min_value=0, max_value=10))
def test_lot_never_exceeds_policy(qty):
    assert calculate_lot(qty) <= policy.max_position_qty
```

### 3.7 再現性（ゴールデン/シード固定）
- 学習・推論・評価コマンドを小区間で実行 → **出力ハッシュ**が一致。  
```bash
pytest -q tests/repro  # /data/golden/** と比較
```

### 3.8 パフォーマンス/レジリエンス
- 目的：Do 層 p95 < 500ms、ブローカー障害時の**安全停止**。  
- ツール：`k6`/`locust`、故障注入（ネットワーク遅延/レート制限）。  
```bash
k6 run tests/perf/do_orders_p95.js
pytest -q tests/resilience -m fault_injection
```

### 3.9 セキュリティ
- SAST/依存脆弱性/シークレットスキャン。  
```bash
bandit -q -r src
pip-audit -r requirements.txt
gitleaks detect --no-banner
```

### 3.10 監視・ルール（Observability）
- Prometheus Rules/Loki クエリの**静的検証**と**リハーサル**。  
```bash
promtool check rules deploy/alerts/noctria.rules.yml
pytest -q tests/observability
```

---

## 4. 環境マトリクス & ゲーティング
| 種別 | dev | stg | prod |
|---|---:|---:|---:|
| Lint/SAST/Contract | ✅ | ✅ | ✅ |
| Unit/Integration | ✅ | ✅ | ✅ |
| E2E（シャドー/低ロット） | ⭕ | ✅ | 🔸（カナリアのみ） |
| Perf/Resilience | ⭕ | ✅ | 🔸（事前掲示） |
| Observability Rehearsal | ✅ | ✅ | ✅ |

> 🔸=本番は**事前告知＆時間帯制限**。  
> 昇格条件：`Strategy-Lifecycle.md` の **G2/G3/G4 ゲート**を満たすこと。

---

## 5. CI/CD（推奨パイプライン）
```mermaid
flowchart LR
  A[PR Open] --> L[Lint/Format/SAST]
  L --> S[Schema/Contract]
  S --> U[Unit]
  U --> I[Integration (Docker test stack)]
  I --> B[Build images + SBOM + Vuln Scan]
  B --> E[E2E (stg, shadow/low-lot)]
  E --> G[Gate: KPI/Alerts/SLA]
  G -->|pass| D[Deploy stg]
  D --> C[Canary prod (7%)]
  C --> R[Promote 30% → 100%]
  G -->|fail| X[Block + Report]
```

**ゲート条件（例）**
- `do_order_latency_seconds` p95 ≤ 0.5s（stg）  
- `do_slippage_pct` p90 ≤ 0.3%（stg, 10m）  
- `kpi_win_rate`（7d）≥ 0.50、`kpi_max_dd_pct`（7d）≤ 8%  
- 重大アラート 0 件（`Observability.md §5`）

---

## 6. ローカル実行（開発者向け）
```bash
# 事前
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# まとめ実行
make test          # lint+unit+contract
make test-full     # + integration + e2e (ローカル最小)
make schemas-check # JSON Schema 静的検証
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
- **合成データ**：シミュレータで **極端値/欠損/レート制限**を再現  
- **シード**：`[1337, 1729, 31415]` を基本（`ModelCard-Prometheus-PPO.md` と整合）

---

## 8. Airflow QA（必須チェック）
- **DAG Import**：`airflow dags list` が**ゼロエラー**  
- **SLA**：`airflow_dag_sla_miss_total` が閾値以下  
- **Dry Runs**：代表タスク `--dry-run` が完了  
- **Backfill 小区間**：UTC 1日で成功、**idempotent**  
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

---

## 10. KPI パイプラインQA（Check/Act）
- **入力**：`/data/execution_logs/*.json`（疑似データ）  
- **出力**：`kpi_summary.json` の **スキーマ/値域/更新時刻** を検証。  
- **Hermes**：説明テキストが**空/不整合**でないこと。

---

## 11. モデルQA（Prometheus/Veritas）
- **推論安定性**：同一入力 → **同一出力**（許容ε）  
- **学習再現**：小区間学習 → 指標±Δ（閾値 3%）  
- **過学習検査**：Train/Test 乖離が**設定範囲内**  
- **安全**：アクションからのロット変換で **境界越えなし**（Noctus シミュレーション）

---

## 12. リリース・ゲーティング & 段階導入
- **カナリア条件**：`Strategy-Lifecycle.md §4.4`（7%→30%→100%、Safemode ON）。  
- **昇格基準**：`§5 ゲート条件` を連続日数クリア、重大アラートゼロ。  
- **ロールバック**：`Runbooks.md §8`。`risk_event` 発火で即時停止検討。

---

## 13. バグ管理 & 優先度
| Severity | 定義 | 例 | 目標応答 |
|---|---|---|---|
| S1 | 安全/財務に重大 | 連続発注/境界無視/監査欠落 | 即時対応・抑制ON |
| S2 | 本番影響大 | p95>0.5s 持続、DAG停止 | 当日内修正/回避 |
| S3 | 影響中 | 一部戦略のみ劣化 | 次リリース |
| S4 | 低 | UI/文言/軽微ログ | バックログ |

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

## 15. カバレッジ & 品質基準
- **ライン**：総合 75% 以上、コア（Plan/Do/Noctus）80% 以上。  
- **Lint**：`ruff/black` をゼロエラー。  
- **スキーマ**：100% 準拠。  
- **パフォーマンス**：Do層 p95 < 0.5s（stg）。

---

## 16. 変更管理（Docs as Code）
- 仕様変更は **同一PR**で本書と関連ドキュメント（`API/Do-Layer-Contract/Runbooks/Config-Registry/Observability`）を更新。  
- 重要な QA 変更は `ADRs/` に記録。

---

## 17. 既知の制約 / TODO
- 本番での**故障注入**は限定的（時間帯制約・影響最小化）  
- 取引所のレート制限変更を**自動追随**する仕組みを強化予定

---

## 18. 変更履歴（Changelog）
- **2025-08-12**: 初版作成（ピラミッド/基準/CI/Airflow/Do契約/モデル/監視/ゲーティング）

