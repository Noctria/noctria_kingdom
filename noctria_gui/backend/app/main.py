from fastapi import FastAPI, HTTPException
import requests
import os

app = FastAPI()

# 環境変数またはハードコードで Airflow の認証情報を設定
AIRFLOW_USERNAME = "airflow"
AIRFLOW_PASSWORD = "airflow"
AIRFLOW_API_URL = "http://172.20.0.4:8080/api/v1/dags"

@app.post("/trigger-dag")
def trigger_dag():
    dag_id = "veritas_master_dag"
    trigger_url = f"{AIRFLOW_API_URL}/{dag_id}/dagRuns"
    payload = {"conf": {"source": "GUI"}}

    try:
        response = requests.post(
            trigger_url,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),  # 🔐 認証追加
            json=payload,
            timeout=5
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return {"message": "✅ DAG triggered successfully!"}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"🚨 DAG起動中にエラー: {str(e)}")
