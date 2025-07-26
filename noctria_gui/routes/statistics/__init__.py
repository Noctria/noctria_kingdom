from fastapi import APIRouter

router = APIRouter()

from .strategy_compare import router as strategy_compare_router

router.include_router(strategy_compare_router, prefix="/strategy_compare")
