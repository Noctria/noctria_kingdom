#!/usr/bin/env python3
# coding: utf-8

"""
📜 Veritas戦略の昇格記録ダッシュボードルート
- 採用ログの一覧表示、検索フィルタ、詳細表示、再評価、Push、CSV出力対応
"""

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.path_config import ACT_LOG_DIR, TOOLS_DIR, GUI_TEMPLATES_DIR
from noctria_gui.services import act_log_service

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))


def parse_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_bool(s):
    if isinstance(s, str):
        return s.lower() in ["true", "1", "on"]
    return None


def normalize_score(log: dict) -> dict:
    """scoreがdictの場合はmeanに変換して統一"""
    score = log.get("score")
    if isinstance(score, dict) and "mean" in score:
        log["score"] = score["mean"]
    return log


@router.get("/act-history", response_class=HTMLResponse)
async def show_act_history(
    request: Request,
    strategy_name: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    min_score: Optional[str] = Query(None),
    max_score: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    pushed: Optional[str] = Query(None),
):
    min_score_val = parse_float(min_score)
    max_score_val = parse_float(max_score)
    pushed_val = parse_bool(pushed)
    strategy_name_val = strategy_name if strategy_name and strategy_name not in ["", "None"] else None
    tag_val_raw = tag if tag and tag not in ["", "None"] else None
    tag_val = act_log_service.normalize_tag(tag_val_raw)
    start_date_val = start_date if start_date and start_date not in ["", "None"] else None
    end_date_val = end_date if end_date and end_date not in ["", "None"] else None

    logs = act_log_service.load_all_act_logs()

    try:
        score_range = (min_score_val, max_score_val) if min_score_val is not None and max_score_val is not None else None
        date_range = (
            datetime.strptime(start_date_val, "%Y-%m-%d"),
            datetime.strptime(end_date_val, "%Y-%m-%d"),
        ) if start_date_val and end_date_val else None

        logs = act_log_service.filter_act_logs(
            logs,
            strategy_name=strategy_name_val,
            tag=tag_val,
            score_range=score_range,
            date_range=date_range,
            pushed=pushed_val,
        )
    except Exception as e:
        print(f"[act_history] ⚠️ フィルターエラー: {e}")

    # ✅ スコア整形（テンプレートで安心して "%.2f" 可）
    logs = [normalize_score(log) for log in logs]

    # ✅ タグ一覧（正規タグ → 表示名）
    tag_map = {}
    for log in logs:
        raw_tag = log.get("tag")
        norm_tag = log.get("normalized_tag", "")
        if norm_tag and raw_tag:
            tag_map[norm_tag] = raw_tag
    tag_list = sorted(tag_map.items())  # List of (normalized_tag, display_tag)

    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "logs": logs,
        "tag_list": tag_list,
        "filters": {
            "strategy_name": strategy_name_val,
            "tag": tag_val,
            "min_score": min_score_val,
            "max_score": max_score_val,
            "start_date": start_date_val,
            "end_date": end_date_val,
            "pushed": pushed_val,
        }
    })


@router.get("/act-history/detail", response_class=HTMLResponse)
async def show_act_detail(request: Request, strategy_name: str = Query(...)):
    log = act_log_service.get_log_by_strategy(strategy_name)
    if not log:
        return HTMLResponse(content="指定された戦略ログが見つかりませんでした。", status_code=404)
    return templates.TemplateResponse("act_history_detail.html", {
        "request": request,
        "log": normalize_score(log)
    })


@router.post("/act-history/repush")
async def repush_strategy(strategy_name: str = Form(...)):
    act_log_service.reset_push_flag(strategy_name)
    return RedirectResponse(url="/act-history", status_code=303)


@router.post("/act-history/reevaluate")
async def reevaluate_strategy(strategy_name: str = Form(...)):
    act_log_service.mark_for_reevaluation(strategy_name)
    return RedirectResponse(url="/act-history", status_code=303)


@router.get("/act-history/export")
async def export_act_log_csv(
    strategy_name: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    min_score: Optional[str] = Query(None),
    max_score: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    pushed: Optional[str] = Query(None),
):
    min_score_val = parse_float(min_score)
    max_score_val = parse_float(max_score)
    pushed_val = parse_bool(pushed)
    strategy_name_val = strategy_name if strategy_name and strategy_name not in ["", "None"] else None
    tag_val_raw = tag if tag and tag not in ["", "None"] else None
    tag_val = act_log_service.normalize_tag(tag_val_raw)
    start_date_val = start_date if start_date and start_date not in ["", "None"] else None
    end_date_val = end_date if end_date and end_date not in ["", "None"] else None

    logs = act_log_service.load_all_act_logs()

    try:
        score_range = (min_score_val, max_score_val) if min_score_val is not None and max_score_val is not None else None
        date_range = (
            datetime.strptime(start_date_val, "%Y-%m-%d"),
            datetime.strptime(end_date_val, "%Y-%m-%d"),
        ) if start_date_val and end_date_val else None

        logs = act_log_service.filter_act_logs(
            logs,
            strategy_name=strategy_name_val,
            tag=tag_val,
            score_range=score_range,
            date_range=date_range,
            pushed=pushed_val,
        )
    except Exception as e:
        print(f"[act_history/export] ⚠️ フィルターエラー: {e}")

    logs = [normalize_score(log) for log in logs]

    if not logs:
        return JSONResponse(status_code=404, content={"detail": "出力可能なログがありません"})

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"veritas_adoptions_{timestamp}.csv"

    success = act_log_service.export_logs_to_csv(logs, output_path)
    if not success:
        return JSONResponse(status_code=500, content={"detail": "CSV出力に失敗しました"})

    return FileResponse(
        output_path,
        filename=output_path.name,
        media_type="text/csv"
    )
