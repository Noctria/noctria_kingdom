from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from typing import Optional
from pathlib import Path

from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from noctria_gui.services.statistics_service import load_statistics_data

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ========================================
# 📊 /statistics - 戦略スコアボード
# ========================================
@router.get("/statistics")
async def show_statistics_dashboard(
    request: Request,
    strategy: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    min_winrate: Optional[float] = Query(None),
    max_dd: Optional[float] = Query(None),
    sort_by: Optional[str] = Query("winrate"),
    order: Optional[str] = Query("desc"),
):
    # 統計データ読み込み
    stats = load_statistics_data()

    # フィルター処理
    def matches(entry):
        if strategy and strategy not in entry["strategy"]:
            return False
        if symbol and symbol != entry["symbol"]:
            return False
        if min_winrate and entry.get("winrate", 0) < min_winrate:
            return False
        if max_dd and entry.get("max_dd", float("inf")) > max_dd:
            return False
        return True

    filtered = list(filter(matches, stats))

    # ソート処理
    reverse = order == "desc"
    filtered.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)

    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "stats": filtered,
        "filters": {
            "strategy": strategy,
            "symbol": symbol,
            "min_winrate": min_winrate,
            "max_dd": max_dd,
            "sort_by": sort_by,
            "order": order,
        }
    })
