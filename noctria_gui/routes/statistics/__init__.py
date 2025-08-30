from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["statistics"])

# 既存の戦略比較ルーターをインクルード
from .strategy_compare import router as strategy_compare_router
router.include_router(strategy_compare_router, prefix="/strategy_compare")

@router.get("/", summary="Statistics Root")
async def statistics_root():
    # リダイレクトを削除して、統計のホームページに遷移
    # ここでリダイレクトを行わず、直接統計ページを表示する
    return RedirectResponse(url="/statistics/dashboard")
