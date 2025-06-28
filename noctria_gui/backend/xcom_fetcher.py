import requests

def fetch_xcom_result(dag_id: str, task_id: str, key: str):
    url = f"http://localhost:8080/api/v1/dags/{dag_id}/dagRuns?order_by=-execution_date"
    resp = requests.get(url, auth=("airflow", "airflow"))
    dag_runs = resp.json().get("dag_runs", [])
    
    if not dag_runs:
        return {"error": "No DAG runs found"}

    latest_run_id = dag_runs[0]["dag_run_id"]

    xcom_url = f"http://localhost:8080/api/v1/dags/{dag_id}/dagRuns/{latest_run_id}/taskInstances/{task_id}/xcomEntries/{key}"
    xcom_resp = requests.get(xcom_url, auth=("airflow", "airflow"))
    
    if xcom_resp.status_code == 200:
        return {"result": xcom_resp.json().get("value")}
    else:
        return {"error": "XCom not found"}
