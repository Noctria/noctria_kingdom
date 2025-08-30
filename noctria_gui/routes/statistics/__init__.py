from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# テンプレート設定
from src.core.path_config import GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service  # <--- 修正: 統計サービスをインポート

router = APIRouter(tags=["statistics"])

# Jinja2 テンプレートのインスタンスを作成
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

# 既存の戦略比較ルーターをインクルード
from .strategy_compare import router as strategy_compare_router
router.include_router(strategy_compare_router, prefix="/strategy_compare")

@router.get("/", summary="Statistics Root", response_class=HTMLResponse)
async def statistics_root(request: Request):
    try:
        # <--- 修正: 統計サービスからサマリーデータを取得 ---
        # 実際の関数名はプロジェクトに合わせてください (例: get_dashboard_stats())
        summary_stats = statistics_service.get_summary_stats()

        # <--- 修正: 取得したデータを "stats" というキーでテンプレートに渡す ---
        return templates.TemplateResponse("statistics_dashboard.html", {
            "request": request,
            "stats": summary_stats
        })
    except Exception as e:
        # <--- 修正: データ取得に失敗した場合のエラーハンドリング ---
        # エラーログを出力するなど、実際の運用に合わせて調整してください
        print(f"Error fetching statistics: {e}")
        # ユーザーには分かりやすいエラーメッセージを表示
        return templates.TemplateResponse("statistics_dashboard.html", {
            "request": request,
            "error": "統計データの取得中にエラーが発生しました。"
        })
