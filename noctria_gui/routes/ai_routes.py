#!/usr/bin/env python3
# coding: utf-8

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

router = APIRouter(prefix="/ai", tags=["AI"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

@router.get("/", summary="AI一覧ページ")
async def ai_list(request: Request):
    # AI名リストをここで取得・生成
    ai_names = ["Aurus", "Levia", "Noctus", "Prometheus", "Veritas"]

    return templates.TemplateResponse("ai_list.html", {
        "request": request,
        "ai_names": ai_names
    })
