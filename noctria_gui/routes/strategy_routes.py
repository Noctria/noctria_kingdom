from fastapi import APIRouter, Request, HTTPException
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

@router.get("/strategies/view", response_class=HTMLResponse)
async def view_strategy(request: Request, name: str):
    veritas_dir = STRATEGIES_DIR / "veritas_generated"
    target_file = veritas_dir / name

    if not target_file.exists() or not target_file.suffix == ".py":
        raise HTTPException(status_code=404, detail="戦略ファイルが存在しません")

    content = target_file.read_text(encoding="utf-8")

    return templates.TemplateResponse("strategies/view.html", {
        "request": request,
        "filename": name,
        "content": content
    })
