# noctria_gui/routes/trigger.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # ✅ 名前統一

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))  # ✅ 統一

@router.get("/trigger", response_class=HTMLResponse)
async def trigger_page(request: Request):
    return templates.TemplateResponse("trigger.html", {"request": request})
