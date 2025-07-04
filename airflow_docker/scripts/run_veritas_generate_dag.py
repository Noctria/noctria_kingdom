import requests
import os
import json
from datetime import datetime

# ✅ Airflow API 設定（.envなどで外部管理可能）
AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
DAG_ID = os.getenv("DAG_ID", "veritas_master_dag")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")

# ✅ 任意のconfパラメータ（JSON文字列で渡す）
# 例: VERITAS_CONF_JSON='{"run_mode": "full", "user_id": 123}'
VERITAS_CONF_JSON = os.getenv("VERITAS_CONF_JSON", "{}")

def trigger_veritas_master_dag():
    trigger_url = f"{AIRFLOW_API_URL}/dags/{DAG_ID}/dagRuns"
    execution_date = datetime.utcnow().isoformat()

    try:
        conf_dict = json.loads(VERITAS_CONF_JSON)
    except json.JSONDecodeError as e:
        print(f"⚠️ confのJSONデコードに失敗しました: {e}")
        conf_dict = {}

    payload = {
        "conf": conf_dict,
        "execution_date": execution_date
    }

    try:
        response = requests.post(
            trigger_url,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload
        )

        if response.status_code in (200, 201):
            print(f"✅ DAG '{DAG_ID}' 起動成功！")
            print("📡 実行情報:", response.json())
        else:
            print(f"❌ DAG起動失敗 ({response.status_code})")
            print(response.text)

    except Exception as e:
        print(f"🚨 通信エラー発生: {e}")

if __name__ == "__main__":
    trigger_veritas_master_dag()
