#!/usr/bin/env python3
# coding: utf-8

"""
Airflow REST API を使った DAG トリガー処理モジュール

- Airflow の Stable REST API を使い、外部から DAG の手動実行をトリガーする
- トリガー時の理由（reason）などを DAG 実行コンテキストの conf に渡せる
- Airflow Webserver の URL、Basic認証情報を環境変数で管理可能
- 追加: Airflowに登録されているDAG一覧を取得する(list_dags)
"""

import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

# .envの変数名に合わせて修正
AIRFLOW_API_BASE_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
AIRFLOW_API_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_API_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")


class AirflowDagTrigger:
    def __init__(
        self,
        base_url: str = AIRFLOW_API_BASE_URL,
        username: str = AIRFLOW_API_USERNAME,
        password: str = AIRFLOW_API_PASSWORD,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)

    def trigger_dag(
        self,
        dag_id: str,
        conf: Optional[Dict[str, Any]] = None,
        execution_date: Optional[str] = None,
        replace_microseconds: bool = True,
    ) -> Dict[str, Any]:
        """
        DAGを手動トリガーする。

        Args:
            dag_id (str): トリガーしたいDAGのID
            conf (dict, optional): DAGに渡す実行コンテキスト。JSON形式でAirflow側に渡される
            execution_date (str, optional): DAGの実行日時。指定しない場合はAirflowが自動割当
            replace_microseconds (bool): execution_dateのマイクロ秒を0にするかどうか（推奨True）

        Returns:
            dict: Airflow API のレスポンス JSON を辞書で返す
        """
        url = f"{self.base_url}/dags/{dag_id}/dagRuns"

        payload = {}
        if conf is not None:
            payload["conf"] = conf

        if execution_date is not None:
            dt = datetime.fromisoformat(execution_date)
            if replace_microseconds:
                dt = dt.replace(microsecond=0)
            payload["execution_date"] = dt.isoformat()

        response = requests.post(url, json=payload, auth=self.auth)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(f"Failed to trigger DAG '{dag_id}': {response.text}") from e

        return response.json()

    def list_dags(self, limit: int = 1000) -> List[str]:
        """
        Airflow REST API からDAG一覧（dag_idのみのリスト）を取得

        Args:
            limit (int): 最大取得数

        Returns:
            List[str]: 登録されているDAGのIDリスト
        """
        url = f"{self.base_url}/dags?limit={limit}"
        response = requests.get(url, auth=self.auth)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(f"Failed to list DAGs: {response.text}") from e

        data = response.json()
        return [d["dag_id"] for d in data.get("dags", [])]


default_trigger = AirflowDagTrigger()

def trigger_dag(
    dag_id: str,
    conf: Optional[Dict[str, Any]] = None,
    execution_date: Optional[str] = None,
) -> Dict[str, Any]:
    return default_trigger.trigger_dag(dag_id=dag_id, conf=conf, execution_date=execution_date)

def list_dags(limit: int = 1000) -> List[str]:
    return default_trigger.list_dags(limit=limit)
