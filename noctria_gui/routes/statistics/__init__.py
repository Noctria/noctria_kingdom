from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# テンプレート設定
from src.core.path_config import GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

router = APIRouter(tags=["statistics"])

# Jinja2 テンプレートのインスタンスを作成
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

# 既存の戦略比較ルーターをインクルード
from .strategy_compare import router as strategy_compare_router
router.include_router(strategy_compare_router, prefix="/strategy_compare")

@router.get("/", summary="Statistics Root", response_class=HTMLResponse)
async def statistics_root(request: Request):
    try:
        # サービスからサマリーデータを取得
        summary_stats = statistics_service.get_summary_stats()

        return templates.TemplateResponse("statistics_dashboard.html", {
            "request": request,
            "stats": summary_stats
        })
    except Exception as e:
        # エラーログに本来の原因を出力
        print(f"!!! Original Error in statistics_service: {e}")
        
        # ユーザーにはエラーメッセージを表示しつつ、テンプレートがクラッシュしないようにする
        return templates.TemplateResponse("statistics_dashboard.html", {
            "request": request,
            "error": "統計データの取得中にエラーが発生しました。",
            "stats": {}  # <--- 修正: エラー時でもstatsを空の辞書として渡す
        })
