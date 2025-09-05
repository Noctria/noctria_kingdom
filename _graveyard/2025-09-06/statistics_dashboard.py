#!/usr/bin/env python3
# coding: utf-8

"""
📊 /statistics - 戦略統計関連の全URLを処理する統合ルーター
- HUDダッシュボード表示 (/dashboard)
- フィルタ・ソート機能
- CSVエクスポート機能 (/export)
- 戦略比較機能 (/strategy_compare)
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

from src.core.path_config import TOOLS_DIR, NOCTRIA_GUI_TEMPLATES_DIR
from noctria_gui.services import statistics_service

# プレフィックスは外部で付与される想定
router = APIRouter(tags=["Statistics"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def show_statistics_dashboard(request: Request):
    """
    📈 HUDスタイル統計ダッシュボードと戦略一覧を表示（フィルタ付き）
    """
    strategy = request.query_params.get("strategy", "").strip() or None
    symbol = request.query_params.get("symbol", "").strip() or None
    start_date = request.query_params.get("start_date", "").strip() or None
    end_date = request.query_params.get("end_date", "").strip() or None

    try:
        # サービスからデータを取得
        all_logs = statistics_service.load_all_logs()
        stats = statistics_service.get_strategy_statistics()
        
        # フィルタリングとソート
        filtered_logs = statistics_service.filter_logs(
            logs=all_logs,
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        sorted_logs = statistics_service.sort_logs(
            logs=filtered_logs,
            sort_key="win_rate",
            descending=True
        )
        
    except Exception as e:
        logging.error(f"Failed to process statistics data: {e}", exc_info=True)
        # エラー発生時も最低限の表示ができるように空のデータを渡す
        return templates.TemplateResponse("statistics_dashboard.html", {
            "request": request,
            "stats": {},
            "statistics": [],
            "strategies": [],
            "symbols": [],
            "filters": {},
            "error": "統計データの処理中にエラーが発生しました。"
        })

    return templates.TemplateResponse("statistics_dashboard.html", {
        "request": request,
        "stats": stats,
        "statistics": sorted_logs,
        "strategies": statistics_service.get_available_strategies(all_logs),
        "symbols": statistics_service.get_available_symbols(all_logs),
        "filters": {
            "strategy": strategy or "",
            "symbol": symbol or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
        },
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
        if not logs:
            raise ValueError("出力する統計ログが存在しません。")
        statistics_service.export_statistics_to_csv(logs, output_path)
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
    ⚔️ 戦略比較ダッシュボードを表示
    """
    strategy_1 = request.query_params.get("strategy_1", "").strip() or None
    strategy_2 = request.query_params.get("strategy_2", "").strip() or None
    
    # 利用可能な戦略リストを取得してテンプレートに渡す
    all_logs = statistics_service.load_all_logs()
    available_strategies = statistics_service.get_available_strategies(all_logs)

    context = {
        "request": request,
        "strategies": available_strategies,
        "strategy_1": strategy_1,
        "strategy_2": strategy_2,
    }

    if strategy_1 and strategy_2:
        if strategy_1 == strategy_2:
            context["error"] = "異なる戦略を選択してください。"
        else:
            try:
                comparison_results = statistics_service.compare_strategies(all_logs, strategy_1, strategy_2)
                context["comparison_results"] = comparison_results
            except Exception as e:
                context["error"] = f"戦略比較の処理中にエラーが発生しました: {e}"

    return templates.TemplateResponse("strategy_compare.html", context)
