from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
import requests

from core.path_config import (
    PDCA_LOG_DIR,
    VERITAS_ORDER_JSON,
    NOCTRIA_GUI_TEMPLATES_DIR,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


# ========================================
# 📜 /pdca - 履歴表示ページ
# ========================================
@router.get("/pdca", response_class=HTMLResponse)
async def show_pdca_dashboard(request: Request):
    log_files = sorted(PDCA_LOG_DIR.glob("*.json"), reverse=True)
    logs = []

    for log_file in log_files:
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        logs.append({
            "filename": log_file.name,
            "path": str(log_file),
            "json_text": content,
        })

    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "logs": logs,
    })


# ========================================
# 🔁 /pdca/replay - 再送命令 & DAGトリガー
# ========================================
@router.post("/pdca/replay")
async def replay_order_from_log(log_path: str = Form(...)):
    airflow_url = os.environ.get("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
    dag_id = "veritas_replay_dag"

    payload = {
        "conf": {"log_path": log_path}
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{airflow_url}/dags/{dag_id}/dagRuns",
            json=payload,
            headers=headers,
            auth=("airflow", "airflow")  # Airflow basic auth
        )

        if response.status_code in [200, 201]:
            print(f"✅ 再送DAG起動成功: {log_path}")
            return RedirectResponse(url="/pdca", status_code=303)
        else:
            print("❌ DAGトリガー失敗:", response.text)
            return JSONResponse(status_code=500, content={"detail": "DAG起動に失敗しました"})

    except Exception as e:
        print("❌ DAG通信エラー:", str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})
