#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca-dashboard - PDCAダッシュボードの画面表示ルート
- クエリパラメータからフィルタを受け取り、テンプレートに渡す
- 現時点ではダミーデータだが、今後の拡張でDBやログから取得可能
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

# ========================================
# ⚙️ ルーター設定
# ========================================
router = APIRouter(
    prefix="/pdca-dashboard",     # すべてのルートはこの接頭辞を持つ
    tags=["PDCA"]                 # FastAPI Swagger用タグ
)

templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ========================================
# 🔍 ダッシュボード表示ルート
# ========================================
@router.get("/", response_class=HTMLResponse)
async def show_pdca_dashboard(request: Request):
    """
    PDCAダッシュボードのメインビュー。
    クエリパラメータからフィルターを取得し、テンプレートに渡す。
    """
    filters = {
        "strategy": request.query_params.get("strategy", ""),
        # 必要に応じて他のフィルター項目も追加可能
        # "symbol": request.query_params.get("symbol", ""),
        # "date_from": request.query_params.get("date_from", ""),
        # "date_to": request.query_params.get("date_to", ""),
    }

    # 📦 PDCAデータ取得（現時点ではダミーデータ）
    pdca_data = [
        # ここに実データ取得処理を記述予定（e.g., from DB or log parser）
        # 例:
        # {
        #     "strategy": "mean_revert_001",
        #     "win_rate": 72.5,
        #     "max_dd": 12.4,
        #     "timestamp": "2025-07-13T12:34:56",
        # },
    ]

    return templates.TemplateResponse("pdca_dashboard.html", {
        "request": request,
        "filters": filters,
        "pdca_logs": pdca_data,
    })

# ========================================
# 🧩 他ルート追加のためのテンプレ
# ========================================
# @router.get("/history", response_class=HTMLResponse)
# async def show_pdca_history(request: Request):
#     # ...
#     return templates.TemplateResponse("pdca_history.html", {"request": request})
