# noctria_gui/routes/trigger.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import GUI_TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/trigger", response_class=HTMLResponse)
async def trigger_page(request: Request):
    """
    🧭 GET /trigger - 王の発令フォームを表示
    """
    return templates.TemplateResponse("trigger.html", {
        "request": request,
        "result": None
    })


@router.post("/trigger", response_class=HTMLResponse)
async def trigger_command(request: Request, manual_reason: str = Form(...)):
    """
    🧨 POST /trigger - 発令処理を実行
    """
    # TODO: ここで Airflow トリガーなどの実処理を呼び出す（仮）
    result = f"📯 発令完了: PDCAサイクルが開始されました！理由: {manual_reason}"

    return templates.TemplateResponse("trigger.html", {
        "request": request,
        "result": result
    })
