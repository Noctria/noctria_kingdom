#!/usr/bin/env python3
# coding: utf-8

"""
📯 King's Decree Trigger Route (v2.0)
- 王命発令（トリガー）画面の表示と、DAG手動実行リクエストの受付を行う
"""

import logging
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# --- 王国の基盤モジュールをインポート ---
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from airflow.api.common.experimental import trigger_dag  # Airflow APIでDAGをトリガー

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# DAGをトリガーする関数
def trigger_airflow_dag(dag_id: str, reason: str):
    try:
        # 実際にAirflow DAGをトリガーする
        trigger_dag(dag_id=dag_id, run_id=f"{dag_id}_manual_{reason}", conf={"reason": reason})
        logging.info(f"DAG『{dag_id}』の起動に成功しました。")
        return {"status": "success", "message": f"DAG『{dag_id}』の起動に成功しました。"}
    except Exception as e:
        logging.error(f"DAG『{dag_id}』の起動に失敗しました: {str(e)}")
        return {"status": "error", "message": f"DAG『{dag_id}』の起動に失敗しました: {str(e)}"}

@router.get("/trigger", response_class=HTMLResponse)
async def get_trigger_page(request: Request):
    """
    GET /trigger - 王命を発令するためのフォーム画面を表示する。
    """
    return templates.TemplateResponse("trigger.html", {"request": request})

@router.post("/trigger")
async def handle_trigger_command(manual_reason: str = Form(...)):
    """
    POST /trigger - 王命を受け取り、指定されたDAGの実行を試みる。
    結果はJSON形式で返す。
    """
    dag_id_to_trigger = "noctria_kingdom_pdca_optimization_loop"
    logging.info(f"王命を受理しました。DAG『{dag_id_to_trigger}』の起動を試みます。理由: {manual_reason}")

    try:
        # 実際のAirflow DAGトリガー処理
        result = trigger_airflow_dag(dag_id=dag_id_to_trigger, reason=manual_reason)
        
        if result['status'] == 'success':
            return JSONResponse(content=result)
        else:
            raise Exception(result['message'])

    except Exception as e:
        error_message = f"王命の発令に失敗しました。詳細: {e}"
        logging.error(error_message, exc_info=True)
        # エラーが発生した場合は、HTTP 500エラーと詳細をJSONで返す
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "王命の発令中に予期せぬ問題が発生しました。",
                "error_details": str(e)
            }
        )
