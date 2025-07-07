#!/usr/bin/env python3
# coding: utf-8

"""
📜 Veritas戦略の昇格記録ダッシュボードルート
- 採用ログの一覧表示、検索フィルタ、詳細表示、再評価、Push、CSV出力対応
"""

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.path_config import ACT_LOG_DIR, TOOLS_DIR, GUI_TEMPLATES_DIR
from noctria_gui.services import act_log_service

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


@router.get("/act-history", response_class=HTMLResponse)
async def show_act_history(
    request: Request,
    strategy_name: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    max_score: Optional[float] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    pushed: Optional[str] = Query(None),
):
    """
    📋 採用戦略ログを一覧表示（検索・絞り込み対応）
    """
    # 空文字や"None"もNone扱いに変換
    if not strategy_name or strategy_name in ["", "None"]:
        strategy_name = None
    if not tag or tag in ["", "None"]:
        tag = None
    if not min_score or min_score in ["", "None"]:
        min_score = None
    if not max_score or max_score in ["", "None"]:
        max_score = None
    if not start_date or start_date in ["", "None"]:
        start_date = None
    if not end_date or end_date in ["", "None"]:
        end_date = None
    if not pushed or pushed in ["", "None"]:
        pushed = None

    # pushed型変換
    if pushed is not None:
        pushed = pushed.lower() in ["true", "1", "on"]

    logs = act_log_service.load_all_act_logs()

    # フィルター処理
    try:
        score_range = (min_score, max_score) if min_score is not None and max_score is not None else None
        date_range = (
            datetime.strptime(start_date, "%Y-%m-%d"),
            datetime.strptime(end_date, "%Y-%m-%d"),
        ) if start_date and end_date else None

        logs = act_log_service.filter_act_logs(
            logs,
            strategy_name=strategy_name,
            tag=tag,
            score_range=score_range,
            date_range=date_range,
            pushed=pushed,
        )
    except Exception as e:
        print(f"[act_history] ⚠️ フィルターエラー: {e}")

    tag_list = sorted({log.get("tag") for log in logs if log.get("tag")})

    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "logs": logs,
        "tag_list": tag_list,
        "filters": {
            "strategy_name": strategy_name,
            "tag": tag,
            "min_score": min_score,
            "max_score": max_score,
            "start_date": start_date,
            "end_date": end_date,
            "pushed": pushed,
        }
    })


@router.get("/act-history/detail", response_class=HTMLResponse)
async def show_act_detail(request: Request, strategy_name: str = Query(...)):
    """
    🔍 指定戦略の詳細ログページ
    """
    log = act_log_service.get_log_by_strategy(strategy_name)
    if not log:
        return HTMLResponse(content="指定された戦略ログが見つかりませんでした。", status_code=404)

    return templates.TemplateResponse("act_history_detail.html", {
        "request": request,
        "log": log
    })


@router.post("/act-history/repush")
async def repush_strategy(strategy_name: str = Form(...)):
    """
    🔁 指定戦略のPushフラグを false にリセット（再Push可能に）
    """
    act_log_service.reset_push_flag(strategy_name)
    return RedirectResponse(url="/act-history", status_code=303)


@router.post("/act-history/reevaluate")
async def reevaluate_strategy(strategy_name: str = Form(...)):
    """
    🔄 指定戦略を再評価対象として記録
    """
    act_log_service.mark_for_reevaluation(strategy_name)
    return RedirectResponse(url="/act-history", status_code=303)


@router.get("/act-history/export")
async def export_act_log_csv(
    strategy_name: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    max_score: Optional[float] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    pushed: Optional[str] = Query(None),
):
    """
    📤 採用戦略ログをCSV形式で出力（検索条件を反映）
    """
    # 空文字や"None"もNone扱いに変換
    if not strategy_name or strategy_name in ["", "None"]:
        strategy_name = None
    if not tag or tag in ["", "None"]:
        tag = None
    if not min_score or min_score in ["", "None"]:
        min_score = None
    if not max_score or max_score in ["", "None"]:
        max_score = None
    if not start_date or start_date in ["", "None"]:
        start_date = None
    if not end_date or end_date in ["", "None"]:
        end_date = None
    if not pushed or pushed in ["", "None"]:
        pushed = None

    # pushed型変換
    if pushed is not None:
        pushed = pushed.lower() in ["true", "1", "on"]

    logs = act_log_service.load_all_act_logs()

    try:
        score_range = (min_score, max_score) if min_score is not None and max_score is not None else None
        date_range = (
            datetime.strptime(start_date, "%Y-%m-%d"),
            datetime.strptime(end_date, "%Y-%m-%d"),
        ) if start_date and end_date else None

        logs = act_log_service.filter_act_logs(
            logs,
            strategy_name=strategy_name,
            tag=tag,
            score_range=score_range,
            date_range=date_range,
            pushed=pushed,
        )
    except Exception as e:
        print(f"[act_history/export] ⚠️ フィルターエラー: {e}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"veritas_adoptions_{timestamp}.csv"

    act_log_service.export_logs_to_csv(logs, output_path)

    return FileResponse(
        output_path,
        filename=output_path.name,
        media_type="text/csv"
    )
