import requests

def trigger_dag(dag_id: str):
    url = f"http://localhost:8080/api/v1/dags/{dag_id}/dagRuns"
    response = requests.post(url, auth=("airflow", "airflow"), json={})
    return {"status": response.status_code, "message": response.json()}
