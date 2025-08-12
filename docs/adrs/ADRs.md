# 🧭 Coding Standards — Noctria Kingdom

**Version:** 1.0  
**Status:** Draft → Adopted (when merged)  
**Last Updated:** 2025-08-12 (JST)

> 目的：Noctria のコード（Plan/Do/Check/Act、API/GUI、DAG/ツール）が**安全・再現可能・読みやすい**状態で進化し続けるための標準を定める。  
> 参照：`../architecture/Architecture-Overview.md` / `../architecture/Plan-Layer.md` / `../operations/Config-Registry.md` / `../operations/Airflow-DAGs.md` / `../observability/Observability.md` / `../security/Security-And-Access.md` / `../qa/Testing-And-QA.md` / `../apis/API.md` / `../apis/Do-Layer-Contract.md`

---

## 1. スコープ & 原則
- スコープ：**Python**（中核）、DAG（Airflow）、API/GUI（FastAPI）、スクリプト、テスト、設定（YAML/JSON Schema）。  
- 原則：
  1) **Guardrails First** — リスク境界・監査・Secrets を常に優先。  
  2) **Clarity over Cleverness** — 可読性と明確な責務分離。  
  3) **Reproducibility** — 同じ入力→同じ出力（シード固定、仕様の明文化）。  
  4) **Docs-as-Code** — 変更は**同一PR**で関連ドキュメントを更新。

---

## 2. 言語・ランタイム・依存
- Python **3.11+** を標準。型ヒント**必須**（後述）。  
- 依存は `requirements.txt / requirements-dev.txt` を**単一情報源**とし、CI で `pip-audit`。  
- OS 時刻は UTC、表示は JST（`Observability.md` に準拠）。

---

## 3. プロジェクト構成（抜粋）
```
src/
  core/...
  plan_data/{collector.py,features.py,statistics.py,analyzer.py}
  strategies/{aurus_singularis.py,levia_tempest.py,noctus_sentinella.py,prometheus_oracle.py,veritas_machina.py,hermes_cognitor.py}
  execution/{order_execution.py,optimized_order_execution.py,broker_adapter.py,generate_order_json.py}
  check/{evaluation.py,...}
  act/{pdca_recheck.py,pdca_push.py,pdca_summary.py}
  api/{main.py,routers/*.py,schemas/*.py}
airflow_docker/dags/*.py
config/{defaults.yml,dev.yml,stg.yml,prod.yml,flags.yml}
docs/**  # ←本書を含む
tests/{unit,integration,e2e,data_quality,observability,repro,perf,resilience}
```

---

## 4. コーディングスタイル
- **フォーマッタ**：`black`（line length 100）  
- **リンタ**：`ruff`（import 順序整列含む）  
- **型検査**：`mypy`（strict: `warn-unused-ignores`, `disallow-any-generics`）  
- **Docstring**：**Google スタイル**を標準、公開関数/クラス/モジュールに必須。  
- **命名**：`snake_case`（関数/変数）、`PascalCase`（クラス）、`UPPER_SNAKE`（定数）

**pyproject.toml（抜粋）**
```toml
[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
select = ["E","F","W","I","B","UP","SIM","PTH","N","C90"]
ignore = ["E203"]
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
disallow_any_generics = true
```

---

## 5. 型ヒント & Docstring（例）
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import TypedDict, Iterable

class ExecResult(TypedDict, total=False):
    symbol: str
    side: str
    avg_price: float
    filled_qty: float
    status: str
    ts: str

@dataclass(frozen=True)
class RiskBounds:
    max_drawdown_pct: float
    max_position_qty: float

def calculate_lot(signal: float, bounds: RiskBounds) -> float:
    """Map a normalized signal [-1,1] to lot size w/ risk bounds.

    Args:
      signal: Normalized action in [-1.0, 1.0].
      bounds: Risk boundaries from Noctus.

    Returns:
      Non-negative lot quantity that never exceeds policy.
    """
    s = max(-1.0, min(1.0, signal))
    qty = abs(s) * bounds.max_position_qty
    return min(qty, bounds.max_position_qty)
```

---

## 6. 例外処理 & エラー設計
- 例外は**意図的に**投げる（`ValueError`, `RuntimeError`, `TimeoutError` など）。  
- API 層では **統一エラー**（`code/message/correlation_id/ts`）に変換（`API.md §2`）。  
- **再試行**：ネットワーク系のみ指数バックオフ、**ビジネス NG** はリトライ禁止。  
- **Idempotency-Key** 必須（書き込み系）。

---

## 7. ロギング（構造化 JSON）
- ログは**構造化 JSON**で `stdout` へ。PII/Secrets は**禁止**（`Security-And-Access.md`）  
- **必須フィールド**：`ts, level, msg, component, correlation_id, env, git`  
- **監査**：Do 層は **`audit_order.json`** を**全件**保存（`Do-Layer-Contract.md §7`）。

```python
log.info(
    "order filled",
    extra={"component":"do.order_execution","order_id":oid,"symbol":sym,"slippage_pct":slip}
)
```

---

## 8. コンフィグ & フラグ
- **SoT**：`config/defaults.yml` → `{env}.yml` → `flags.yml` → Secrets（Vault/ENV）  
- 直接ハードコード禁止。読み込みは**専用モジュール**経由で、**スキーマ検証**を実施。  
- 本番では `risk_safemode: true` を既定（`Config-Registry.md`）。

---

## 9. データ & スキーマ
- すべての JSON I/O は **JSON Schema** で検証（`docs/schemas/`）。  
- `features_dict.json` / `kpi_summary.json` / `exec_result.json` などは**改訂は後方互換**（Breaking は v2 へ）。  
- 時刻は **UTC ISO-8601** 固定。

---

## 10. API / HTTP 標準
- ヘッダ：`Authorization`, `Idempotency-Key`, `X-Correlation-ID` は**必須**（書き込み）。  
- ステータス：2xx/4xx/5xx の基本準拠。  
- **SSE/Webhook** は署名検証 & リトライ設計を実装（`API.md §10`）。  
- **入力検証**：pydantic でスキーマ適合 → ビジネス検証（Noctus ガード）→ 実行。

---

## 11. テスト & カバレッジ
- **ピラミッド**：Unit → Contract → Integration → E2E（`Testing-And-QA.md`）。  
- **基準**：コア 80% / 総合 75% 以上、契約スキーマ 100%。  
- **ゴールデン**：再現性テストでハッシュ一致。  
- 失敗時の**最小再現**（ログ/入力）を残す。

---

## 12. パフォーマンス & 並行性
- I/O は非同期 or バッチ化、CPU 集約は**ベクトル化/Numba**。  
- Do 層：**分割発注** + **間引き** + **レート制限**（Adapter 吸収）。  
- Airflow：`max_active_runs`/`pools` で**影響範囲を限定**（`Airflow-DAGs.md`）。

---

## 13. セキュリティ（コード観点）
- **Secrets** をコードに置かない。ENV/Vault から注入。  
- **入力バリデーション**徹底（pydantic/JSON Schema）。  
- ログに**機密/PII を出力禁止**。  
- **Two-Person Rule** 対象の変更はレビュー＋King 承認（`Security-And-Access.md`）。

---

## 14. Git / PR / コミット規約
- **Conventional Commits** 準拠：`feat: ...` / `fix: ...` / `docs: ...` / `refactor: ...` / `chore: ...` など。  
- **PR テンプレ**に**影響範囲・テスト・Runbooks/Config更新**を必ず記載。  
- **同一PR**で関連ドキュメント更新（Docs-as-Code）。

**PR チェックリスト（要約）**
- [ ] 仕様変更のドキュメント更新（該当章）  
- [ ] JSON Schema/契約テストがパス  
- [ ] ログと監査の項目が適切  
- [ ] Secrets/PII が混入していない  
- [ ] しきい値変更は `Config-Registry.md` を更新

---

## 15. pre-commit / CI（必須）
**`.pre-commit-config.yaml`（抜粋）**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks: [{id: black}]
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.5.0
    hooks: [{id: ruff, args: ["--fix"]}]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks: [{id: mypy}]
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks: [{id: gitleaks}]
```

**CI（要件）**
- Lint/Format/Type/Contract の**4点セット**が PR で必須。  
- Prometheus Rules/Loki クエリは静的検証（`promtool check rules`）。

---

## 16. 具体例（パターン集）

### 16.1 CLI エントリ
```python
import argparse, json
from src.plan_data.features import run as run_features

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out_df", required=True)
    p.add_argument("--out_dict", required=True)
    args = p.parse_args()
    run_features(args.inp, args.out_df, args.out_dict)

if __name__ == "__main__":
    main()
```

### 16.2 FastAPI ルータ（Idempotency + Correlation）
```python
from fastapi import APIRouter, Header, HTTPException, Request
router = APIRouter(prefix="/api/v1/do", tags=["do"])

@router.post("/orders")
async def create_order(req: Request,
                       idempotency_key: str = Header(..., alias="Idempotency-Key"),
                       corr: str | None = Header(None, alias="X-Correlation-ID")):
    body = await req.json()
    # validate -> risk guard -> execute
    # return unified response
    return {"status":"ACCEPTED"}
```

### 16.3 Airflow DAG（共通デフォルト適用）
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import timedelta
from _defaults import DEFAULTS

with DAG(dag_id="pdca_plan_workflow",
         schedule_interval="0 5 * * 1-5",
         default_args=DEFAULTS,
         catchup=False, tags=["pdca","plan"]) as dag:
    PythonOperator(task_id="collect_market_data", python_callable=collect)
```

---

## 17. レビュー観点チェックリスト（詳細）
- **安全**：Noctus 境界を越えない／抑制時の分岐あり／監査が残る  
- **構成**：ハードコードなし／SoT 準拠／スキーマ適合  
- **品質**：テスト範囲十分／再現性（シード/ゴールデン）  
- **観測**：構造化ログ／メトリクス／トレース／Correlation ID  
- **パフォーマンス**：無駄なループなし／I/O バッチ／並列/バックオフ  
- **セキュリティ**：Secrets/PII 排除／署名検証／RBAC  
- **ドキュメント**：関連章の更新／Release-Notes 追記

---

## 18. 変更履歴（Changelog）
- **2025-08-12**: 初版作成（スタイル/型/例外/ログ/Config/Schema/API/テスト/CI/レビュー）
