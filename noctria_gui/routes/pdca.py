from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from noctria_gui.services.airflow_trigger import trigger_dag
from core.path_config import PDCA_LOG_DIR, VERITAS_ORDER_JSON
from pathlib import Path
import json

router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")
templates.env.filters["from_json"] = lambda x: json.loads(x)

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

@router.get("/pdca", response_class=HTMLResponse)
async def pdca_dashboard(request: Request):
    histories = load_pdca_logs()
    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "histories": histories,
        "message": None
    })

@router.post("/pdca", response_class=HTMLResponse)
async def trigger_pdca(request: Request):
    result = trigger_dag("veritas_pdca_dag")
    histories = load_pdca_logs()
    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "histories": histories,
        "message": result
    })

# ✅ 再実行API：指定されたログファイルで EA命令JSON を上書き
@router.post("/pdca/replay", response_class=HTMLResponse)
async def replay_pdca(filename: str = Form(...)):
    log_path = PDCA_LOG_DIR / filename
    if not log_path.exists():
        return HTMLResponse(content=f"ログが見つかりません: {filename}", status_code=404)

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            content = json.load(f)

        VERITAS_ORDER_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(VERITAS_ORDER_JSON, "w", encoding="utf-8") as out:
            json.dump(content, out, indent=2, ensure_ascii=False)

        return RedirectResponse(url="/pdca", status_code=303)
    except Exception as e:
        return HTMLResponse(content=f"再実行失敗: {e}", status_code=500)
