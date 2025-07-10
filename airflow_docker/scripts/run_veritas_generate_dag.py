#!/usr/bin/env python3
# coding: utf-8

"""
📡 Veritas Master DAG トリガースクリプト
- Airflow REST API 経由で DAG を起動
- .env 経由の conf 渡しに対応
"""

import os
import json
import requests
from datetime import datetime
from requests.exceptions import RequestException

# ============================
# 🔧 環境変数 or デフォルト設定
# ============================
AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
DAG_ID = os.getenv("DAG_ID", "veritas_master_dag")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")
VERITAS_CONF_JSON = os.getenv("VERITAS_CONF_JSON", "{}")

# ============================
# 🚀 DAG起動処理
# ============================
def trigger_veritas_master_dag():
    trigger_url = f"{AIRFLOW_API_URL}/dags/{DAG_ID}/dagRuns"

    try:
        conf_dict = json.loads(VERITAS_CONF_JSON)
    except json.JSONDecodeError as e:
        print(f"⚠️ confのJSONデコードに失敗しました: {e}")
        conf_dict = {}

    payload = {
        "conf": conf_dict
        # execution_date は省略可能（Airflowが自動生成）
    }

    try:
        response = requests.post(
            trigger_url,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload,
            timeout=10
        )

        if response.status_code in (200, 201):
            print(f"✅ DAG '{DAG_ID}' 起動成功！")
            print("📡 実行情報:", json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"❌ DAG起動失敗 (status: {response.status_code})")
            print(response.text)

    except RequestException as e:
        print(f"🚨 通信エラー: {e}")

# ============================
# 🔧 実行ブロック
# ============================
if __name__ == "__main__":
    trigger_veritas_master_dag()
