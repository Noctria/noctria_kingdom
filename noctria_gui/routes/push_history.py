#!/usr/bin/env python3
# coding: utf-8

"""
📦 Push履歴の表示・検索・詳細確認・CSV出力ルート
"""

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import json
import csv
import io

from core.path_config import PUSH_LOG_DIR, GUI_TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(GUI_TEMPLATES_DIR))

# デフォルトページング設定
PAGE_SIZE = 50

@router.get("/push-history", response_class=HTMLResponse)
def view_push_history(
    request: Request,
    strategy: str = Query(default="", description="戦略名フィルタ"),
    tag: str = Query(default="", description="タグフィルタ"),
    start_date: str = Query(default="", description="開始日 YYYY-MM-DD"),
    end_date: str = Query(default="", description="終了日 YYYY-MM-DD"),
    keyword: str = Query(default="", description="メッセージ内検索キーワード"),
    page: int = Query(default=1, ge=1, description="ページ番号")
):
    """
    📋 Push履歴一覧（フィルタ付き・ページング対応）
    """
    logs = []

    if not PUSH_LOG_DIR.exists():
        PUSH_LOG_DIR.mkdir(parents=True)

    for file in sorted(PUSH_LOG_DIR.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            log = json.load(f)

            if strategy and strategy not in log.get("strategy", ""):
                continue
            if tag and tag != log.get("tag", ""):
                continue
            if keyword and keyword.lower() not in log.get("message", "").lower():
                continue

            log_date = log.get("timestamp", "")[:10]  # YYYY-MM-DD
            if start_date and log_date < start_date:
                continue
            if end_date and log_date > end_date:
                continue

            logs.append(log)

    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    tag_list = sorted({log.get("tag") for log in logs if log.get("tag")})

    # ---- ページング ----
    total_count = len(logs)
    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    # 範囲外のページ指定は1に矯正
    if page > total_pages:
        page = total_pages
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paged_logs = logs[start:end]

    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": paged_logs,
        "tag_list": tag_list,
        "filters": {
            "strategy": strategy,
            "tag": tag,
            "start_date": start_date,
            "end_date": end_date,
            "keyword": keyword
        },
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": PAGE_SIZE,
    })


@router.get("/push-history/export")
def export_push_history_csv(
    strategy: str = Query(default="", description="戦略名フィルタ"),
    tag: str = Query(default="", description="タグフィルタ"),
    start_date: str = Query(default="", description="開始日 YYYY-MM-DD"),
    end_date: str = Query(default="", description="終了日 YYYY-MM-DD"),
    keyword: str = Query(default="", description="メッセージ内検索キーワード")
):
    """
    📤 Push履歴CSV出力（フィルタ適用）
    """
    logs = []

    for file in sorted(PUSH_LOG_DIR.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            log = json.load(f)

            if strategy and strategy not in log.get("strategy", ""):
                continue
            if tag and tag != log.get("tag", ""):
                continue
            if keyword and keyword.lower() not in log.get("message", "").lower():
                continue

            log_date = log.get("timestamp", "")[:10]
            if start_date and log_date < start_date:
                continue
            if end_date and log_date > end_date:
                continue

            logs.append(log)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["timestamp", "strategy", "tag", "message", "signature"])
    writer.writeheader()

    for log in logs:
        writer.writerow({
            "timestamp": log.get("timestamp", ""),
            "strategy": log.get("strategy", ""),
            "tag": log.get("tag", ""),
            "message": log.get("message", ""),
            "signature": log.get("signature", "")
        })

    output.seek(0)
    filename = f"push_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })


@router.get("/push-history/detail", response_class=HTMLResponse)
def push_history_detail(request: Request, timestamp: str):
    """
    🔍 指定Pushログの詳細表示
    """
    log_path = PUSH_LOG_DIR / f"{timestamp}.json"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found")

    with open(log_path, "r", encoding="utf-8") as f:
        log = json.load(f)

    return templates.TemplateResponse("push_history_detail.html", {
        "request": request,
        "log": log
    })
