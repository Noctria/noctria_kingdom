#!/usr/bin/env python3
# coding: utf-8

"""
📯 King's Decree Trigger Route (v4.0)
- 王命発令（トリガー）画面の表示
- Airflow DAG一覧の取得
- 王Noctria API経由でDAG起動コマンドを発令
"""

import logging
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import httpx

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from src.core.dag_trigger import list_dags  # trigger_dagは廃止

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
    POST /trigger - 王Noctria API経由で王命/DAG起動コマンドを発令
    """
    logging.info(f"王命（Noctria API経由）: DAG『{dag_id}』を理由『{manual_reason}』で起動")
    try:
        # 👑 王Noctria APIに統一委譲
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/king/command",
                json={
                    "command": "trigger_dag",
                    "args": {
                        "dag_id": dag_id,
                        "reason": manual_reason
                    }
                }
            )
        if response.status_code == 200:
            data = response.json()
            res = {
                "status": "success",
                "message": f"DAG『{dag_id}』の王命起動に成功しました。",
                "dag_id": dag_id,
                "decision_id": data.get("decision_id"),
                "king_response": data,
                "reason": manual_reason
            }
            logging.info(res["message"])
            return JSONResponse(content=res)
        else:
            err = response.text
            logging.error(f"王API経由でDAG起動失敗: {err}")
            raise Exception(err)
    except Exception as e:
        error_message = f"王命の発令（API経由）に失敗: {e}"
        logging.error(error_message, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "王命APIの発令中に予期せぬ問題が発生しました。",
                "error_details": str(e)
            }
        )
