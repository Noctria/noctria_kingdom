# noctria_gui/routes/trigger.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.path_config import GUI_TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

@router.get("/trigger", response_class=HTMLResponse)
async def trigger_page(request: Request):
    return templates.TemplateResponse("trigger.html", {"request": request})
