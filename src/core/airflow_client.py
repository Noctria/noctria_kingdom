# src/core/airflow_client.py
# -*- coding: utf-8 -*-
"""
Airflow REST API クライアント（2.x / /api/v1）

- 目的: DAG Run のトリガ／実行確認／ヘルスチェック等を安全に提供
- 特徴:
  * Bearer Token または Basic 認証の両対応
  * requests.Session による接続の再利用
  * verify_ssl の環境変数制御（既定: False）
  * conf に datetime 等が入っても ISO8601(Z) で安全に JSON 化
  * /health, /version は base_url が /api/v1 でも自動でルートに切替
  * 既存実装との互換: trigger_dag(…) / list_dag_runs(…) / get_task_instances(…) / get_log(…)

環境変数（どちらかの名前に対応: *API_* / 互換名）:
- AIRFLOW_API_BASE_URL / AIRFLOW_BASE_URL   (例: http://localhost:8080/api/v1)
- AIRFLOW_API_TOKEN     / AIRFLOW_TOKEN     (Bearer 認証。優先)
- AIRFLOW_API_USERNAME  / AIRFLOW_USERNAME  (Basic 認証)
- AIRFLOW_API_PASSWORD  / AIRFLOW_PASSWORD  (Basic 認証)
- AIRFLOW_API_VERIFY_SSL / AIRFLOW_VERIFY_SSL (true/false/1/0。未指定時 False)
- AIRFLOW_API_TIMEOUT_SEC / AIRFLOW_TIMEOUT_SEC (HTTPタイムアウト秒, 既定: 15)

主要メソッド:
- health() -> dict
- version() -> dict
- trigger_dag_run(dag_id, conf=None, logical_date=None, note=None, dag_run_id=None) -> dict
- trigger_dag(dag_id, conf=None, **kwargs) -> dict   # 互換エイリアス
- get_dag_run(dag_id, dag_run_id) -> dict
- list_dag_runs(dag_id, state=None, limit=100, order_by="-start_date", offset=0) -> List[dict]
- get_task_instances(dag_id, dag_run_id) -> List[dict]
- get_log(dag_id, dag_run_id, task_id, try_number=1) -> str
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------
def _parse_bool_env(val: Optional[str], default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _now_utc_iso() -> str:
    # 末尾Zで統一（AirflowはISO8601を受け付ける）
    return datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _json_default(o: Any) -> Any:
    # datetime -> ISO8601Z、その他は str()
    if isinstance(o, datetime):
        if o.tzinfo is None:
            o = o.replace(tzinfo=timezone.utc)
        return o.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    # pydantic BaseModel など
    if hasattr(o, "dict"):
        try:
            return o.dict()
        except Exception:
            pass
    if hasattr(o, "model_dump"):
        try:
            return o.model_dump()
        except Exception:
            pass
    return str(o)


# -----------------------------------------------------------------------------
# client
# -----------------------------------------------------------------------------
class AirflowRESTClient:
    """
    Airflow 2.x REST API v1 クライアント
    参考: https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        timeout_sec: int = 15,
        session: Optional[requests.Session] = None,
    ) -> None:
        env_base = (
            os.getenv("AIRFLOW_API_BASE_URL")
            or os.getenv("AIRFLOW_BASE_URL")
            or "http://localhost:8080/api/v1"
        ).rstrip("/")
        self.base_url = (base_url or env_base).rstrip("/")

        # ルート側URL（/api/v1 を含むなら削って root を保持）
        self._root_base = self.base_url
        if self._root_base.endswith("/api/v1"):
            self._root_base = self._root_base[: -len("/api/v1")]

        self.token = token or os.getenv("AIRFLOW_API_TOKEN") or os.getenv("AIRFLOW_TOKEN")
        self.username = username or os.getenv("AIRFLOW_API_USERNAME") or os.getenv("AIRFLOW_USERNAME")
        self.password = password or os.getenv("AIRFLOW_API_PASSWORD") or os.getenv("AIRFLOW_PASSWORD")

        if verify_ssl is None:
            verify_ssl = _parse_bool_env(os.getenv("AIRFLOW_API_VERIFY_SSL") or os.getenv("AIRFLOW_VERIFY_SSL"), default=False)
        self.verify_ssl = bool(verify_ssl)

        self.timeout_sec = int(os.getenv("AIRFLOW_API_TIMEOUT_SEC") or os.getenv("AIRFLOW_TIMEOUT_SEC") or timeout_sec)
        self._session = session or requests.Session()

        if not (self.token or (self.username and self.password)):
            raise RuntimeError(
                "AirflowRESTClient: 認証情報が不足しています。"
                "AIRFLOW_API_TOKEN もしくは AIRFLOW_API_USERNAME/AIRFLOW_API_PASSWORD を設定してください。"
            )

    # ----------------------------
    # 内部ユーティリティ
    # ----------------------------
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _auth(self) -> Optional[Tuple[str, str]]:
        # Bearer Token がある場合は Basic 認証は使わない
        if self.token:
            return None
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def _request(self, method: str, path: str, *, use_root: bool = False, **kwargs) -> requests.Response:
        base = self._root_base if use_root else self.base_url
        url = f"{base}{path}"
        # 既定の headers / auth / verify / timeout を補完
        kwargs.setdefault("headers", self._headers())
        kwargs.setdefault("auth", self._auth())
        kwargs.setdefault("verify", self.verify_ssl)
        kwargs.setdefault("timeout", self.timeout_sec)
        resp = self._session.request(method.upper(), url, **kwargs)
        # エラー時はHTTPError
        resp.raise_for_status()
        return resp

    # ----------------------------
    # パブリック API
    # ----------------------------
    def health(self) -> Dict[str, Any]:
        """
        Airflow Webserver のヘルス確認。
        多くの環境で /health は Web ルート直下にあるため、/api/v1 付きでも root に打ち直す。
        """
        r = self._request("GET", "/health", use_root=True)
        return r.json()

    def version(self) -> Dict[str, Any]:
        """
        Airflow Webserver のバージョン情報（root直下）。
        """
        r = self._request("GET", "/version", use_root=True)
        return r.json()

    def trigger_dag_run(
        self,
        dag_id: str,
        conf: Optional[Dict[str, Any]] = None,
        logical_date: Optional[str | datetime] = None,
        note: Optional[str] = None,
        dag_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        DAG Run を起動する。
        POST /dags/{dag_id}/dagRuns

        Args:
            dag_id: 対象DAGのID
            conf:   DAGに渡す conf（JSON シリアライズ可能）
            logical_date: ISO8601文字列 or datetime（省略時は now UTC）
            note:   Airflow 2.7+ の任意メモ（未対応の環境では Airflow 側が無視 or 400 を返す可能性）
            dag_run_id: 明示 run_id（省略時はAirflow側で自動生成）
        """
        if isinstance(logical_date, datetime):
            logical_date = _json_default(logical_date)  # ISO8601Z
        payload: Dict[str, Any] = {
            "conf": conf or {},
            "logical_date": logical_date or _now_utc_iso(),
        }
        if dag_run_id:
            payload["dag_run_id"] = dag_run_id
        if note:
            payload["note"] = note

        data = json.dumps(payload, default=_json_default)
        r = self._request("POST", f"/dags/{dag_id}/dagRuns", data=data)
        return r.json()

    # 互換エイリアス（既存GUIから呼ばれる）
    def trigger_dag(self, dag_id: str, *, conf: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        return self.trigger_dag_run(dag_id=dag_id, conf=conf, **kwargs)

    def get_dag_run(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """
        単一 DAG Run を取得。
        GET /dags/{dag_id}/dagRuns/{dag_run_id}
        """
        r = self._request("GET", f"/dags/{dag_id}/dagRuns/{dag_run_id}")
        return r.json()

    def list_dag_runs(
        self,
        dag_id: str,
        state: Optional[str] = None,
        limit: int = 100,
        order_by: str = "-start_date",
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        DAG Run の一覧を取得（新しい順が既定）。
        GET /dags/{dag_id}/dagRuns
        戻り値は List[dict]（GUI互換）
        """
        params: Dict[str, Any] = {
            "limit": max(1, int(limit)),
            "order_by": order_by,
            "offset": max(0, int(offset)),
        }
        if state:
            params["state"] = state
        r = self._request("GET", f"/dags/{dag_id}/dagRuns", params=params)
        data = r.json()
        if isinstance(data, dict) and "dag_runs" in data:
            return list(data["dag_runs"])
        if isinstance(data, list):
            return data
        return []

    def get_task_instances(self, dag_id: str, dag_run_id: str) -> List[Dict[str, Any]]:
        """
        DAG Run 配下の Task Instance 一覧。
        GET /dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances
        """
        r = self._request("GET", f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances")
        data = r.json()
        if isinstance(data, dict) and "task_instances" in data:
            return list(data["task_instances"])
        if isinstance(data, list):
            return data
        return []

    def get_log(self, dag_id: str, dag_run_id: str, task_id: str, try_number: int = 1) -> str:
        """
        タスクログ取得（Airflowのバージョン差異によりエンドポイントが複数あるため、2通りを試す）
        """
        # パターン1: /dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{try_number}
        path1 = f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{try_number}"
        try:
            data1 = self._request("GET", path1, params={"full_content": "true"}).json()
            if isinstance(data1, dict) and "content" in data1:
                return data1.get("content") or ""
        except Exception:
            pass

        # パターン2: /dags/{dag_id}/taskInstances/{task_id}/logs/{try_number}
        path2 = f"/dags/{dag_id}/taskInstances/{task_id}/logs/{try_number}"
        try:
            data2 = self._request("GET", path2, params={"full_content": "true"}).json()
            if isinstance(data2, dict) and "content" in data2:
                return data2.get("content") or ""
        except Exception:
            pass
        return ""


# -----------------------------------------------------------------------------
# factory
# -----------------------------------------------------------------------------
def make_airflow_client() -> AirflowRESTClient:
    """
    既定の環境変数から AirflowRESTClient を構築。
    """
    base = os.getenv("AIRFLOW_API_BASE_URL") or os.getenv("AIRFLOW_BASE_URL") or None
    token = os.getenv("AIRFLOW_API_TOKEN") or os.getenv("AIRFLOW_TOKEN") or None
    user = os.getenv("AIRFLOW_API_USERNAME") or os.getenv("AIRFLOW_USERNAME") or None
    pwd = os.getenv("AIRFLOW_API_PASSWORD") or os.getenv("AIRFLOW_PASSWORD") or None
    verify = _parse_bool_env(os.getenv("AIRFLOW_API_VERIFY_SSL") or os.getenv("AIRFLOW_VERIFY_SSL"), default=False)
    timeout = int(os.getenv("AIRFLOW_API_TIMEOUT_SEC") or os.getenv("AIRFLOW_TIMEOUT_SEC") or "15")

    return AirflowRESTClient(
        base_url=base,
        token=token,
        username=user,
        password=pwd,
        verify_ssl=verify,
        timeout_sec=timeout,
    )
