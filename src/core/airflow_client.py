# src/core/airflow_client.py
# -*- coding: utf-8 -*-
"""
Airflow REST API クライアント（2.x / /api/v1）
- 目的: DAG Run のトリガ／ヘルスチェック等の最小ユースケースを安全に提供
- 特徴:
  * Bearer Token または Basic 認証の両対応
  * requests.Session による接続の再利用
  * verify_ssl の環境変数制御（既定: False）
  * conf に datetime 等が入っても ISO8601 で安全に JSON 化

環境変数:
- AIRFLOW_API_BASE_URL   (例: http://localhost:8080/api/v1)
- AIRFLOW_API_TOKEN      (Bearer 認証。優先される)
- AIRFLOW_API_USERNAME   (Basic 認証)
- AIRFLOW_API_PASSWORD   (Basic 認証)
- AIRFLOW_API_VERIFY_SSL (true/false/1/0。未指定時 False)

主要メソッド:
- health() -> dict
- trigger_dag_run(dag_id, conf=None, logical_date=None, note=None, dag_run_id=None) -> dict
- get_dag_run(dag_id, dag_run_id) -> dict
- list_dag_runs(dag_id, state=None, limit=100, order_by="-start_date") -> dict
"""

from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import requests


def _parse_bool_env(val: Optional[str], default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _now_utc_iso() -> str:
    # 末尾Zで統一
    return datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _json_default(o: Any) -> Any:
    # datetime -> ISO8601Z、その他は str()
    if isinstance(o, datetime):
        if o.tzinfo is None:
            o = o.replace(tzinfo=timezone.utc)
        return o.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    # pydantic の BaseModel など
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
        env_base = os.getenv("AIRFLOW_API_BASE_URL", "http://localhost:8080/api/v1").rstrip("/")
        self.base_url = (base_url or env_base).rstrip("/")

        self.token = token or os.getenv("AIRFLOW_API_TOKEN")
        self.username = username or os.getenv("AIRFLOW_API_USERNAME")
        self.password = password or os.getenv("AIRFLOW_API_PASSWORD")

        if verify_ssl is None:
            verify_ssl = _parse_bool_env(os.getenv("AIRFLOW_API_VERIFY_SSL"), default=False)
        self.verify_ssl = bool(verify_ssl)

        self.timeout_sec = int(timeout_sec)

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

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        # 既定の headers / auth / verify / timeout を補完
        kwargs.setdefault("headers", self._headers())
        kwargs.setdefault("auth", self._auth())
        kwargs.setdefault("verify", self.verify_ssl)
        kwargs.setdefault("timeout", self.timeout_sec)
        resp = self._session.request(method.upper(), url, **kwargs)
        # エラー時は例外（HTTPError）を投げる
        resp.raise_for_status()
        return resp

    # ----------------------------
    # パブリック API
    # ----------------------------
    def health(self) -> Dict[str, Any]:
        """
        Airflow Webserver のヘルス確認。
        GET /health
        """
        r = self._request("GET", "/health")
        return r.json()

    def version(self) -> Dict[str, Any]:
        """
        Airflow Webserver のバージョン情報。
        GET /version
        """
        r = self._request("GET", "/version")
        return r.json()

    def trigger_dag_run(
        self,
        dag_id: str,
        conf: Optional[Dict[str, Any]] = None,
        logical_date: Optional[str] = None,
        note: Optional[str] = None,
        dag_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        DAG Run を起動する。
        POST /dags/{dag_id}/dagRuns

        Args:
            dag_id: 対象DAGのID
            conf:   DAGに渡す conf（JSON シリアライズ可能）
            logical_date: ISO8601文字列（省略時は now UTC）
            note:   Airflow 2.7+ の任意メモ（フィールド未対応の環境では無視される）
            dag_run_id: 明示 run_id（省略時はAirflow側で自動生成）

        Returns:
            API の JSON レスポンス
        """
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
    ) -> Dict[str, Any]:
        """
        DAG Run の一覧を取得。
        GET /dags/{dag_id}/dagRuns
        """
        params: Dict[str, Any] = {
            "limit": max(1, int(limit)),
            "order_by": order_by,
            "offset": max(0, int(offset)),
        }
        if state:
            params["state"] = state
        r = self._request("GET", f"/dags/{dag_id}/dagRuns", params=params)
        return r.json()


# 簡易ファクトリ
def make_airflow_client() -> AirflowRESTClient:
    """
    既定の環境変数から AirflowRESTClient を構築。
    """
    return AirflowRESTClient()
