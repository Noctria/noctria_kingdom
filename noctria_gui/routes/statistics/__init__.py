from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# テンプレート設定
from src.core.path_config import GUI_TEMPLATES_DIR

router = APIRouter(tags=["statistics"])

# Jinja2 テンプレートのインスタンスを作成
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

# 既存の戦略比較ルーターをインクルード
from .strategy_compare import router as strategy_compare_router
router.include_router(strategy_compare_router, prefix="/strategy_compare")

@router.get("/", summary="Statistics Root", response_class=HTMLResponse)
async def statistics_root(request: Request):
    # リダイレクトを削除し、直接統計ダッシュボードページを表示する
    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "message": "Welcome to the statistics dashboard. Use '/statistics/strategy_compare' to view strategy comparison."
    })
