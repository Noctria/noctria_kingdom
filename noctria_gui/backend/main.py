from fastapi import FastAPI
from backend.dag_runner import trigger_dag
from backend.xcom_fetcher import fetch_xcom_result

app = FastAPI()

@app.post("/trigger-dag")
def run_noctria_kingdom():
    return trigger_dag(dag_id="noctria_kingdom_dag")

@app.get("/get-result")
def get_decision_result():
    return fetch_xcom_result(dag_id="noctria_kingdom_dag", task_id="noctria_final_decision", key="final_action")
