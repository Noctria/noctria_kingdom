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
# from src.core.dag_trigger import trigger_dag # 将来的にDAG実行モジュールをインポートする想定

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


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
        # 実際のAirflow DAGトリガー処理（将来的に有効化）
        # from src.core.dag_trigger import trigger_dag
        # result = trigger_dag(dag_id=dag_id_to_trigger, reason=manual_reason)
        
        # ダミー処理
        import time
        import random
        time.sleep(2)  # 処理にかかる時間をシミュレート
        if random.random() < 0.9:  # 90%の確率で成功
            result = {
                "status": "success",
                "message": f"王命は滞りなく発令されました。DAG『{dag_id_to_trigger}』が起動しました。",
                "dag_id": dag_id_to_trigger,
                "reason": manual_reason
            }
            logging.info(f"DAG『{dag_id_to_trigger}』の起動に成功しました。")
            return JSONResponse(content=result)
        else:
            raise Exception("Airflowスケジューラへの接続に失敗しました。")

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
