import requests
import json
import time
from datetime import datetime


class VeritasAirflowExecutor:
    def __init__(self, airflow_host="http://localhost:8080", auth=None):
        self.airflow_host = airflow_host.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
        }
        if auth:
            self.headers["Authorization"] = f"Basic {auth}"  # Base64 encoded user:pass

    def trigger_dag(self, dag_id, conf=None):
        """指定DAGを起動"""
        endpoint = f"{self.airflow_host}/api/v1/dags/{dag_id}/dagRuns"
        dag_run_id = f"{dag_id}__{datetime.utcnow().isoformat()}"
        payload = {
            "conf": conf or {},
            "dag_run_id": dag_run_id
        }

        response = requests.post(endpoint, headers=self.headers, data=json.dumps(payload))
        response.raise_for_status()
        print(f"🚀 DAG起動: {dag_id} ➜ {dag_run_id}")
        return dag_run_id

    def wait_for_completion(self, dag_id, dag_run_id, poll_interval=5):
        """DAGの完了を待機"""
        endpoint = f"{self.airflow_host}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
        while True:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            state = response.json().get("state", "unknown")
            print(f"⏳ 実行中... DAG状態 = {state}")
            if state in ("success", "failed"):
                return state
            time.sleep(poll_interval)

    def get_xcom_result(self, dag_id, dag_run_id, task_id, key="return_value"):
        """XComから戦略結果を取得"""
        endpoint = f"{self.airflow_host}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/xcomEntries/{key}"
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json().get("value", None)

    def run_strategy(self, dag_id, task_id, conf=None, xcom_key="return_value"):
        """戦略DAGを実行し、XComの予測結果を取得"""
        dag_run_id = self.trigger_dag(dag_id, conf=conf)
        status = self.wait_for_completion(dag_id, dag_run_id)
        if status == "success":
            result = self.get_xcom_result(dag_id, dag_run_id, task_id, key=xcom_key)
            print(f"✅ XCom取得成功: {result}")
            return result
        else:
            print(f"❌ DAG失敗: {dag_id}")
            return None


# ✅ テスト実行例（Prometheus）
if __name__ == "__main__":
    executor = VeritasAirflowExecutor(airflow_host="http://localhost:8080")

    mock_market_data = {
        "price": 1.2345,
        "volume": 1000,
        "sentiment": 0.8,
        "trend_strength": 0.7,
        "volatility": 0.15,
        "order_block": 0.6,
        "institutional_flow": 0.8,
        "short_interest": 0.5,
        "momentum": 0.9,
        "trend_prediction": 0.6,
        "liquidity_ratio": 1.2
    }

    result = executor.run_strategy(
        dag_id="prometheus_strategy_dag",
        task_id="prometheus_forecast_task",
        conf={"market_data": mock_market_data},
        xcom_key="prometheus_forecast"
    )

    print(f"🎯 最終判断（Prometheus）: {result}")
