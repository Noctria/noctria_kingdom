#!/usr/bin/env python3
# coding: utf-8

"""
📜 Veritas Adoption Log Route (v2.0)
- 採用ログの一覧表示、フィルタリング、詳細表示、非同期でのアクション実行に対応
"""

import logging
from fastapi import APIRouter, Request, Form, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from typing import Optional, List, Dict, Any

# --- 王国の基盤モジュールをインポート ---
from src.core.path_config import TOOLS_DIR, NOCTRIA_GUI_TEMPLATES_DIR
from noctria_gui.services import act_log_service

# ロガー設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/act-history", tags=["act-history"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


# --- 依存性注入：ログフィルタリング処理 ---
def get_filtered_logs(
    strategy_name: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    pushed: Optional[bool] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """
    クエリパラメータに基づいてログをフィルタリングする共通関数。
    """
    try:
        logs = act_log_service.load_all_act_logs()

        date_range = None
        if start_date and end_date:
            date_range = (
                datetime.strptime(start_date, "%Y-%m-%d"),
                datetime.strptime(end_date, "%Y-%m-%d"),
            )

        filtered = act_log_service.filter_act_logs(
            logs,
            strategy_name=strategy_name,
            tag=act_log_service.normalize_tag(tag),
            date_range=date_range,
            pushed=pushed,
        )

        # 🔒 normalize_score() 内で score_mean を常に保証しておくこと
        return [act_log_service.normalize_score(log) for log in filtered]

    except Exception as e:
        logging.error("ログのフィルタリング中にエラーが発生しました", exc_info=True)
        return []


# --- HTML表示用ルート ---
@router.get("", response_class=HTMLResponse)
async def show_act_history(
    request: Request,
    logs: List[Dict[str, Any]] = Depends(get_filtered_logs)
):
    """
    GET /act-history - 採用ログの一覧を表示
    """
    tag_set = set()
    for log in logs:
        tag_set.update(log.get("tags", []))

    return templates.TemplateResponse("act_history.html", {
        "request": request,
        "logs": logs,
        "tag_list": sorted(tag_set),
    })


# --- 詳細表示ルート ---
@router.get("/detail/{log_id}", response_class=HTMLResponse)
async def show_act_detail(request: Request, log_id: str):
    """
    GET /act-history/detail/{log_id} - 単一ログの詳細表示
    """
    log = act_log_service.get_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="指定された戦略ログが見つかりませんでした。")

    return templates.TemplateResponse("act_history_detail.html", {
        "request": request,
        "log": act_log_service.normalize_score(log)
    })


# --- 戦略再Pushルート ---
@router.post("/repush", response_class=JSONResponse)
async def repush_strategy(strategy_name: str = Form(...)):
    """
    POST /act-history/repush - 戦略のPushフラグをリセット
    """
    logging.info(f"戦略『{strategy_name}』の再Push命令を受理しました。")
    try:
        act_log_service.reset_push_flag(strategy_name)
        return {"status": "success", "message": f"戦略『{strategy_name}』を再Push可能にしました。"}
    except Exception as e:
        logging.error("再Push処理中にエラーが発生しました", exc_info=True)
        raise HTTPException(status_code=500, detail=f"再Push処理中にエラー: {e}")


# --- 戦略再評価マークルート ---
@router.post("/reevaluate", response_class=JSONResponse)
async def reevaluate_strategy(strategy_name: str = Form(...)):
    """
    POST /act-history/reevaluate - 戦略に再評価フラグを付与
    """
    logging.info(f"戦略『{strategy_name}』の再評価命令を受理しました。")
    try:
        act_log_service.mark_for_reevaluation(strategy_name)
        return {"status": "success", "message": f"戦略『{strategy_name}』に再評価マークを付けました。"}
    except Exception as e:
        logging.error("再評価マーク処理中にエラーが発生しました", exc_info=True)
        raise HTTPException(status_code=500, detail=f"再評価マーク処理中にエラー: {e}")


# --- CSVエクスポート ---
@router.get("/export", response_class=FileResponse)
async def export_act_log_csv(
    logs: List[Dict[str, Any]] = Depends(get_filtered_logs)
):
    """
    GET /act-history/export - フィルタリング結果をCSV出力
    """
    if not logs:
        raise HTTPException(status_code=404, detail="エクスポート対象のログが見つかりません。")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"veritas_adoptions_{timestamp}.csv"

    success = act_log_service.export_logs_to_csv(logs, output_path)
    if not success:
        raise HTTPException(status_code=500, detail="CSVファイルのエクスポートに失敗しました。")

    return FileResponse(
        output_path,
        filename=output_path.name,
        media_type="text/csv"
    )
