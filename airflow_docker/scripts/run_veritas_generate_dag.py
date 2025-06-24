import requests
import os
from datetime import datetime

# ✅ 設定：Airflow Webserver のエンドポイント
AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
DAG_ID = "veritas_master_dag"

# ✅ 認証情報（必要に応じて変更）
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")

def trigger_veritas_master_dag():
    trigger_url = f"{AIRFLOW_API_URL}/dags/{DAG_ID}/dagRuns"
    execution_date = datetime.utcnow().isoformat()

    payload = {
        "conf": {},  # 任意の設定パラメータをここで渡せる
        "execution_date": execution_date
    }

    try:
        response = requests.post(
            trigger_url,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload
        )

        if response.status_code == 200:
            print(f"✅ DAG '{DAG_ID}' 起動成功！")
            print("📡 実行情報:", response.json())
        else:
            print(f"❌ DAG起動失敗 ({response.status_code})")
            print(response.text)

    except Exception as e:
        print(f"🚨 エラー発生: {e}")

if __name__ == "__main__":
    trigger_veritas_master_dag()
