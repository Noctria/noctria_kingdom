from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["statistics"])

from .strategy_compare import router as strategy_compare_router
router.include_router(strategy_compare_router, prefix="/strategy_compare")

@router.get("/", summary="Statistics Root")
async def statistics_root():
    # ここでは /statistics/strategy_compare へリダイレクト
    return RedirectResponse(url="/statistics/strategy_compare")
