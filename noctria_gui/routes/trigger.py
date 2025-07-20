#!/usr/bin/env python3
# coding: utf-8

"""
📯 King's Decree Trigger Route (v3.1)
- 王命発令（トリガー）画面の表示、DAG手動実行リクエストの受付、DAG一覧取得
"""

import logging
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from src.core.dag_trigger import trigger_dag, list_dags

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


@router.get("/trigger", response_class=HTMLResponse)
async def get_trigger_page(request: Request):
    """
    GET /trigger - 王命を発令するためのフォーム画面を表示し、DAG一覧も取得。
    """
    try:
        dag_list = list_dags()
    except Exception as e:
        logging.error(f"Airflow DAG一覧取得に失敗: {e}", exc_info=True)
        dag_list = []
    return templates.TemplateResponse("trigger.html", {
        "request": request,
        "dag_list": dag_list
    })


@router.post("/trigger")
async def handle_trigger_command(
    dag_id: str = Form(...),
    manual_reason: str = Form(...)
):
    """
    POST /trigger - 王命を受け取り、指定されたDAGの実行を試みる。
    結果はJSON形式で返す。
    """
    logging.info(f"王命を受理：DAG『{dag_id}』を理由『{manual_reason}』で起動")

    try:
        result = trigger_dag(
            dag_id=dag_id,
            conf={"reason": manual_reason}
        )
        if isinstance(result, dict) and result.get("dag_run_id"):
            res = {
                "status": "success",
                "message": f"DAG『{dag_id}』の起動に成功しました。",
                "dag_id": dag_id,
                "dag_run_id": result.get("dag_run_id"),
                "reason": manual_reason
            }
            logging.info(res["message"])
            return JSONResponse(content=res)
        else:
            # レスポンスが不正、または失敗メッセージ
            err = result.get("message") if isinstance(result, dict) else str(result)
            logging.error(f"DAG『{dag_id}』起動APIエラー: {err}")
            raise Exception(err)
    except Exception as e:
        error_message = f"王命の発令に失敗: {e}"
        logging.error(error_message, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "王命の発令中に予期せぬ問題が発生しました。",
                "error_details": str(e)
            }
        )
