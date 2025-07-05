from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from core.path_config import STRATEGIES_DIR

router = APIRouter(tags=["strategy"])
templates = Jinja2Templates(directory="noctria_gui/templates")

@router.get("/strategies", response_class=HTMLResponse)
async def list_strategies(request: Request):
    veritas_dir = STRATEGIES_DIR / "veritas_generated"
    strategy_files = sorted(veritas_dir.glob("*.py"))

    strategy_names = [f.name for f in strategy_files]

    return templates.TemplateResponse("strategies/list.html", {
        "request": request,
        "strategies": strategy_names
    })
