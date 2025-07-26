from fastapi import APIRouter

router = APIRouter()

from .statistics_dashboard import router as dashboard_router
from .statistics_detail import router as detail_router
# 他サブルーターがあればここでimport

router.include_router(dashboard_router, prefix="/dashboard")
router.include_router(detail_router, prefix="/detail")
# 他サブルーターも同様にinclude_routerで統合

