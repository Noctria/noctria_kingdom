from fastapi import APIRouter

# 親ルーター
router = APIRouter(tags=["statistics"])

# サブルーターのインポート
from .strategy_compare import router as strategy_compare_router

# サブルーターを /statistics/strategy_compare にマウント
router.include_router(strategy_compare_router, prefix="/strategy_compare")
