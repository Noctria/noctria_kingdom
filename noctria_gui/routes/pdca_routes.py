#!/usr/bin/env python3
# coding: utf-8

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# プロジェクトのコアモジュールをインポート
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR

# ========================================
# ⚙️ ルーターとテンプレートのセットアップ
# ========================================
router = APIRouter(
    prefix="/pdca-dashboard", # このルーターの全パスは /pdca-dashboard から始まる
    tags=["PDCA"]           # FastAPIのドキュメント用のタグ
)

templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ========================================
# 🔀 ルートハンドラー
# ========================================

@router.get("/", response_class=HTMLResponse)
async def show_pdca_dashboard(request: Request):
    """
    PDCAダッシュボードページを表示します。
    テンプレートが必要とする `filters` 変数を渡します。
    """
    # 修正点: テンプレートが必要とする 'filters' 変数を生成
    filters = {
        "strategy": request.query_params.get("strategy", ""),
        # 他にフィルター項目があれば、同様にクエリパラメータから取得
        # "status": request.query_params.get("status", "all"),
    }

    # PDCAダッシュボードに必要なデータをここで取得・処理する
    # (例: pdca_logs = get_pdca_logs(filters))
    pdca_data = [
        # ... (データベースなどから取得したデータ) ...
    ]

    context = {
        "request": request,
        "filters": filters, # 生成したfiltersをテンプレートに渡す
        "pdca_logs": pdca_data, # 実際のデータも渡す
    }
    
    return templates.TemplateResponse("pdca_dashboard.html", context)

# 他のPDCA関連のルート（例: /history, /summary）もこのファイルに追加できます
# @router.get("/history", response_class=HTMLResponse)
# async def show_pdca_history(request: Request):
#     # ...
#     return templates.TemplateResponse("pdca_history.html", {"request": request})

