from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from noctria_gui.services.airflow_trigger import trigger_dag
from pathlib import Path
import json

router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")
templates.env.filters["from_json"] = lambda x: json.loads(x)

PDCA_LOG_DIR = Path("logs/pdca")

def load_pdca_logs():
    histories = []
    for subdir in sorted(PDCA_LOG_DIR.iterdir(), reverse=True):
        if subdir.is_dir():
            record = {"id": subdir.name, "files": []}
            for file in subdir.glob("*"):
                record["files"].append({
                    "name": file.name,
                    "content": file.read_text(encoding="utf-8")
                })
            histories.append(record)
    return histories

@router.get("/pdca", response_class=HTMLResponse)
def dashboard(request: Request):
    histories = load_pdca_logs()
    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "histories": histories,
        "message": None
    })

@router.post("/pdca", response_class=HTMLResponse)
def trigger_pdca(request: Request):
    result = trigger_dag("veritas_pdca_dag")
    histories = load_pdca_logs()
    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "histories": histories,
        "message": result
    })
