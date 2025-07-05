from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from noctria_gui.services.strategy_handler import process_uploaded_strategy

router = APIRouter()
templates = Jinja2Templates(directory="noctria_gui/templates")

@router.get("/upload-strategy", response_class=HTMLResponse)
def upload_form(request: Request):
    return templates.TemplateResponse("upload_strategy.html", {"request": request, "result": None})

@router.post("/upload-strategy", response_class=HTMLResponse)
async def upload_strategy(request: Request, file: UploadFile = File(...)):
    result = await process_uploaded_strategy(file)
    return templates.TemplateResponse("upload_strategy.html", {"request": request, "result": result})
