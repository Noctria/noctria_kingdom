from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from noctria_gui.services.airflow_trigger import trigger_dag
from core.path_config import PDCA_LOG_DIR
from pathlib import Path
import json

# ✅ FastAPIテンプレート読み込み（Jinja2 with filter）
router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")
templates.env.filters["from_json"] = lambda x: json.loads(x)

# ✅ PDCAログを読み込んで整形
def load_pdca_logs():
    histories = []
    if not PDCA_LOG_DIR.exists():
        return histories

    for file in sorted(PDCA_LOG_DIR.glob("*.json"), reverse=True):
        try:
            content = json.loads(file.read_text(encoding="utf-8"))
            histories.append({
                "id": file.stem,
                "filename": file.name,
                "content": content,
            })
        except Exception as e:
            histories.append({
                "id": file.stem,
                "filename": file.name,
                "content": {
                    "error": f"読み込み失敗: {e}"
                },
            })
    return histories

# ✅ GET: ダッシュボード表示
@router.get("/pdca", response_class=HTMLResponse)
async def pdca_dashboard(request: Request):
    histories = load_pdca_logs()
    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "histories": histories,
        "message": None
    })

# ✅ POST: DAGトリガー後に再表示
@router.post("/pdca", response_class=HTMLResponse)
async def trigger_pdca(request: Request):
    result = trigger_dag("veritas_pdca_dag")
    histories = load_pdca_logs()
    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "histories": histories,
        "message": result
    })
