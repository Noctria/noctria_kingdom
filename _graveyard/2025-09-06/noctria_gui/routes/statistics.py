from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path

from src.core.path_config import TOOLS_DIR, GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"]
)

# Jinja2Templatesのインスタンス化
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def statistics_home(request: Request):
    """
    /statistics ルートへのアクセスは /statistics/dashboard へリダイレクト
    """
    return RedirectResponse(url="/statistics/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
async def show_statistics(request: Request):
    """
    📈 統計スコアダッシュボードを表示（フィルタ付き）
    - /statistics または /statistics/dashboard どちらでもアクセス可能
    """
    strategy = request.query_params.get("strategy", "").strip() or None
    symbol = request.query_params.get("symbol", "").strip() or None
    start_date = request.query_params.get("start_date", "").strip() or None
    end_date = request.query_params.get("end_date", "").strip() or None

    try:
        logs = statistics_service.load_all_logs()
        filtered = statistics_service.filter_logs(
            logs=logs,
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        sorted_logs = statistics_service.sort_logs(
            logs=filtered,
            sort_key="win_rate",
            descending=True
        )
        stats = statistics_service.get_strategy_statistics()  # ここで集計データを取得
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"統計データの処理中にエラーが発生しました: {e}")

    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "statistics": sorted_logs,
        "strategies": statistics_service.get_available_strategies(logs),
        "symbols": statistics_service.get_available_symbols(logs),
        "filters": {
            "strategy": strategy or "",
            "symbol": symbol or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
        },
        "stats": stats  # stats をテンプレートに渡す
    })


@router.get("/export")
async def export_statistics_csv():
    """
    📤 統計スコア一覧をCSVでエクスポート
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"strategy_statistics_{timestamp}.csv"

    try:
        logs = statistics_service.load_all_logs()
        sorted_logs = statistics_service.sort_logs(
            logs=logs,
            sort_key="win_rate",
            descending=True
        )
        if not sorted_logs:
            raise ValueError("出力する統計ログが存在しません。")

        statistics_service.export_statistics_to_csv(sorted_logs, output_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSVエクスポートに失敗しました: {e}")

    return FileResponse(
        path=output_path,
        filename=output_path.name,
        media_type="text/csv"
    )


@router.get("/strategy_compare", response_class=HTMLResponse)
async def strategy_compare(request: Request):
    """
    戦略比較ダッシュボードを表示
    - 戦略間の比較を行う画面を表示
    """
    strategy_1 = request.query_params.get("strategy_1", "").strip() or None
    strategy_2 = request.query_params.get("strategy_2", "").strip() or None

    if not strategy_1 or not strategy_2:
        raise HTTPException(status_code=400, detail="両方の戦略を選択してください。")

    try:
        logs = statistics_service.load_all_logs()
        
        # 戦略1と戦略2の両方をフィルタリング
        filtered_1 = statistics_service.filter_logs(logs=logs, strategy=strategy_1)
        filtered_2 = statistics_service.filter_logs(logs=logs, strategy=strategy_2)
        
        # 戦略比較のロジックを適用
        comparison_results = statistics_service.compare_strategies(filtered_1, filtered_2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"戦略比較の処理中にエラーが発生しました: {e}")

    return templates.TemplateResponse("strategy_compare.html", {
        "request": request,
        "comparison_results": comparison_results,
        "strategy_1": strategy_1 or "",
        "strategy_2": strategy_2 or "",
    })
