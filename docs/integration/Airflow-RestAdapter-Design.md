# Integration: Airflow REST Adapter 設計
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Platform / PDCA

関連文書:
- `docs/apis/PDCA-Recheck-API-Spec.md`
- `docs/airflow/DAG-PDCA-Recheck.md`
- `docs/platform/Config-Reference-DoLayer.md`
- `docs/security/Secrets-Policy.md`

---

## 0. 目的
API 層（GUI/PDCA サービス）から **Airflow REST API** を安全に叩くためのアダプタを定義。  
- 冪等・リトライ・レート・トレーシングを**一箇所**に封じ込める。  
- エラー/HTTP を**正準の reason_code**へマップし、上位 API からの利用を簡素化。

---

## 1. 対象 Airflow API（Stable v1）
- `POST  /api/v1/dags/{dag_id}/dagRuns` … DAG 実行の作成（conf 付き）
- `GET   /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}` … 状態取得
- `GET   /api/v1/dags/{dag_id}/dagRuns?limit&offset&order_by` … 一覧取得
- （将来）`PATCH /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}` … キャンセル等

> 認証は **Basic** もしくは **Bearer（TokenAuth）**。本設計では TokenAuth を推奨。

---

## 2. コンフィグ（.env と整合）
| 変数 | 既定 | 説明 |
|---|---|---|
| `AF_BASE_URL` | `http://airflow-webserver:8080` | Airflow Webserver |
| `AF_AUTH_MODE` | `token` | `token` or `basic` |
| `AF_TOKEN` | なし | TokenAuth のトークン |
| `AF_BASIC_USER` | なし | Basic のユーザ |
| `AF_BASIC_PASS` | なし | Basic のパスワード |
| `AF_TIMEOUT_SEC` | `10` | HTTP タイムアウト |
| `AF_RETRY_MAX` | `3` | 最大リトライ回数 |
| `AF_RETRY_BACKOFF` | `0.5` | 係数（指数バックオフ） |
| `AF_RATE_RPS` | `5` | クライアント側レート制御（トークンバケット） |
| `AF_TLS_VERIFY` | `true` | HTTPS 検証（内部CAならパス指定可） |

---

## 3. インタフェース
```python
class AirflowRestAdapter:
    def __init__(self, base_url: str, auth: Auth, timeout: float, limiter: RateLimiter):
        ...

    def trigger_dag(
        self, dag_id: str, conf: dict, *, request_id: str, trace_id: str | None = None
    ) -> TriggerResult:
        """POST /dags/{dag_id}/dagRuns を叩いて run_id を返す。
        冪等: request_id（ULID）を conf に含めて上位で管理。"""

    def get_dag_run(self, dag_id: str, run_id: str) -> DagRunStatus:
        """GET /dags/{dag_id}/dagRuns/{run_id}"""

    def list_dag_runs(self, dag_id: str, limit: int = 100, order_by: str = "-execution_date") -> DagRunsPage:
        """GET /dags/{dag_id}/dagRuns"""
```

---

## 4. エラーと reason_code 対応
| 事象 | HTTP | reason_code | 上位の扱い |
|---|---|---|---|
| タイムアウト | - | `AIRFLOW_TIMEOUT` | 502 返却（再試行可） |
| 接続不可 | - | `AIRFLOW_DOWN` | 502/503（状況により） |
| 4xx 入力不正 | 400/422 | `AIRFLOW_BAD_REQUEST` | 400 返却 |
| 認証失敗 | 401/403 | `AIRFLOW_UNAUTHORIZED` | 401/403 返却 |
| Webserver 内部エラー | 5xx | `AIRFLOW_ERROR` | 502/500 返却 |
| 不明/パース失敗 | - | `AIRFLOW_UNKNOWN` | 500 返却 |

> 上位 API のマッピングは `PDCA-Recheck-API-Spec.md` のエラー表に整合。

---

## 5. リトライ方針
- 対象: `AIRFLOW_TIMEOUT`, `AIRFLOW_DOWN`, `5xx`（**idempotent** な操作のみ）
- バックオフ: `sleep = AF_RETRY_BACKOFF * (2 ** retry)`（jitter 付与）
- 最大: `AF_RETRY_MAX` 回（既定 3）

> `trigger_dag` は **Airflow 側が冪等ではない**ため、**上位 request_id による重複抑止**を前提に**安全に再送**する。  
> conf 内に `request_id` を必ず含め、GUI/API 側の SoT（`pdca_requests`）と突合する。

---

## 6. Rate Limit（クライアント側）
- トークンバケット（例: `AF_RATE_RPS=5`, バースト 10）  
- 全 API 呼び出し前に `acquire()`。過負荷時は待機 or `429` 擬似返し。  
- 監視: `airflow.adapter.rate_limited_total`

---

## 7. セキュリティ
- 認証情報は **Secrets Backend** / 環境変数で注入  
- TLS: `AF_TLS_VERIFY=true` 推奨（社内CA使用時は CA パスを設定）  
- ログは **マスク**: `Authorization` ヘッダは出力禁止  
- conf ログはサニタイズ（PII/秘密を含めない）

---

## 8. 監視・トレース
- Metrics:
  - `airflow.adapter.requests_total{endpoint,outcome}`  
  - `airflow.adapter.latency_ms{endpoint}` (histogram)  
  - `airflow.adapter.retries_total{endpoint}`  
  - `airflow.adapter.rate_limited_total`
- Logs（JSON）:
  - `endpoint, dag_id, run_id?, http_status, reason_code, latency_ms, request_id, trace_id`
- Tracing:
  - span: `airflow.trigger` / `airflow.get_run`  
  - attributes: `dag_id`, `run_id`, `http_status`（200 系のみ）

---

## 9. 疑似コード（同期版）
```python
import time, json, random
import httpx

class AirflowRestAdapter:
    def __init__(self, base_url, auth_hdr, timeout=10, rps=5):
        self.base_url = base_url.rstrip("/")
        self.auth_hdr = auth_hdr  # {"Authorization": "Bearer ..."}
        self.timeout = timeout
        self.rps = rps
        self.client = httpx.Client(timeout=timeout, verify=True)

    def _headers(self):
        return {"Accept": "application/json", "Content-Type": "application/json", **self.auth_hdr}

    def _retryable(self, code):  # 5xx or network
        return code is None or 500 <= code <= 599

    def _sleep_backoff(self, i, base=0.5):
        time.sleep(base * (2 ** i) + random.random() * 0.1)

    def trigger_dag(self, dag_id, conf: dict, request_id: str, trace_id: str | None = None):
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns"
        payload = {"conf": {**conf, "request_id": request_id}}
        if trace_id:
            payload["conf"]["trace_id"] = trace_id

        last_err = None
        for attempt in range(1, int(getenv("AF_RETRY_MAX", 3)) + 1):
            try:
                resp = self.client.post(url, headers=self._headers(), json=payload)
                if resp.status_code in (200, 201, 202):
                    data = resp.json()
                    return {"status": "ok", "run_id": data.get("dag_run_id") or data.get("run_id")}
                if self._retryable(resp.status_code):
                    last_err = ("AIRFLOW_ERROR", resp.status_code, resp.text)
                    self._sleep_backoff(attempt-1, float(getenv("AF_RETRY_BACKOFF", 0.5)))
                    continue
                # 非リトライ系
                rc = "AIRFLOW_UNAUTHORIZED" if resp.status_code in (401,403) else \
                     "AIRFLOW_BAD_REQUEST" if resp.status_code in (400,422) else "AIRFLOW_ERROR"
                return {"status":"error","reason_code":rc,"http_status":resp.status_code,"body":resp.text}
            except httpx.RequestError as e:
                last_err = ("AIRFLOW_DOWN", None, str(e))
                self._sleep_backoff(attempt-1, float(getenv("AF_RETRY_BACKOFF", 0.5)))
                continue
            except httpx.TimeoutException as e:
                last_err = ("AIRFLOW_TIMEOUT", None, str(e))
                self._sleep_backoff(attempt-1, float(getenv("AF_RETRY_BACKOFF", 0.5)))
                continue
        rc, code, body = last_err or ("AIRFLOW_UNKNOWN", None, "")
        return {"status":"error","reason_code":rc,"http_status":code,"body":body}
```

> 非同期版（`httpx.AsyncClient`）は同様の構造で実装可能。GUI API サービスのイベントループ内で使用する場合はこちらを推奨。

---

## 10. 入出力バリデーション
- **入力**（上位 API → adapter）
  - `dag_id`: `/^[a-zA-Z0-9_\-]+$/`  
  - `conf`: JSON オブジェクト、サイズ上限（例: 64KB）  
  - `request_id`: ULID/UUID 形式必須  
- **出力**（adapter → 上位 API）
  - 成功: `{"status":"ok","run_id":"..."}`
  - 失敗: `{"status":"error","reason_code":"...","http_status":<int?>}`

---

## 11. テスト計画（Adapter 単体）
- **T-101**: 正常トリガ → `ok`+`run_id`  
- **T-102**: 5xx → リトライ後成功  
- **T-103**: タイムアウト → リトライ後失敗（`AIRFLOW_TIMEOUT`）  
- **T-104**: 401/403 → `AIRFLOW_UNAUTHORIZED`  
- **T-105**: 422 → `AIRFLOW_BAD_REQUEST`  
- **T-106**: レート制御超過 → 待機 or 擬似 `429` を返す  
- **T-107**: conf に `request_id` が含まれることを検証

---

## 12. 運用ノート
- Airflow 側の**並列度**や**max_active_runs** と衝突しないように `AF_RATE_RPS` をチューニング。  
- 障害時は adapter のメトリクスで「Airflow 側の劣化」を素早く検知（SLO アラート連動）。  
- 将来のキャンセル API（PATCH）にも同一エラー/リトライ方針を適用。

---

## 13. 変更履歴
- **2025-08-24**: 初版（trigger/get/list、リトライ/レート、reason_code マップ、擬似実装）
