#!/usr/bin/env python3
# coding: utf-8

"""
📜 Veritas戦略の昇格記録ダッシュボードルート
- 採用ログの一覧表示、フィルタ、再評価、Push、CSV出力対応
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path

from core.path_config import ACT_LOG_DIR, TOOLS_DIR, GUI_TEMPLATES_DIR
from noctria_gui.services import act_log_service

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/act-history", response_class=HTMLResponse)
async def show_act_history(request: Request, only_unpushed: bool = False):
    """
    📋 採用戦略ログを一覧表示
    - 未Pushフィルター機能あり
    """
    logs = act_log_service.load_all_act_logs()
    if only_unpushed:
        logs = [log for log in logs if not log.get("pushed", False)]

    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "logs": logs,
        "only_unpushed": only_unpushed
    })


@router.post("/act-history/repush")
async def repush_strategy(strategy_name: str = Form(...)):
    """
    🔁 指定戦略のPushフラグを強制的に false に戻す
    （再Push可能にする）
    """
    act_log_service.force_unpush_flag(strategy_name)
    return RedirectResponse(url="/act-history", status_code=303)


@router.post("/act-history/reevaluate")
async def reevaluate_strategy(strategy_name: str = Form(...)):
    """
    🔄 指定戦略を再評価フェーズに回す（評価結果へ戻す）
    """
    act_log_service.move_to_evaluation(strategy_name)
    return RedirectResponse(url="/act-history", status_code=303)


@router.get("/act-history/export")
async def export_act_log_csv():
    """
    📤 採用戦略ログをCSV形式で出力
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"veritas_adoptions_{timestamp}.csv"

    logs = act_log_service.load_all_act_logs()
    act_log_service.export_act_logs_to_csv(logs, output_path)

    return FileResponse(
        output_path,
        filename=output_path.name,
        media_type="text/csv"
    )
