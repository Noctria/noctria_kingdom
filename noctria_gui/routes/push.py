#!/usr/bin/env python3
# coding: utf-8

"""
📦 Push機能統合ルート (v2.0)
- Airflow DAG経由のGitHub Pushトリガー
- Pushログの閲覧／検索／CSV出力／詳細表示
"""

import logging
import json
import csv
import io
import os
from fastapi import APIRouter, Request, Query, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_config.pyのリファクタリングに合わせて、正しい変数名をインポート
from src.core.path_config import PUSH_LOG_DIR, NOCTRIA_GUI_TEMPLATES_DIR
# from src.noctria_gui.services import push_service # 将来的にロジックをサービス層に分離する想定

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/push", tags=["Push"])
# ✅ 修正: 正しい変数名を使用
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# --- Pydanticモデル定義 ---
class DAGTriggerResponse(BaseModel):
    detail: str
    dag_run_id: Optional[str] = None
    response_body: Optional[str] = None

# --- 依存性注入（DI）によるログフィルタリングの共通化 ---
def get_filtered_push_logs(
    strategy: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """クエリパラメータに基づいてPushログをフィルタリングする共通関数"""
    logs = []
    if not PUSH_LOG_DIR.exists():
        logging.warning(f"Pushログディレクトリが存在しません: {PUSH_LOG_DIR}")
        return []

    for file_path in PUSH_LOG_DIR.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                log = json.load(f)
            
            # フィルタリングロジック
            if strategy and strategy.lower() not in log.get("strategy", "").lower(): continue
            if tag and tag != log.get("tag", ""): continue
            if keyword and keyword.lower() not in log.get("message", "").lower(): continue
            
            log_date_str = log.get("timestamp", "")[:10]
            if start_date and log_date_str < start_date: continue
            if end_date and log_date_str > end_date: continue
            
            logs.append(log)
        except Exception as e:
            logging.error(f"Pushログファイルの読み込みに失敗しました: {file_path}, エラー: {e}")
            
    return logs

# --- ルート定義 ---

@router.post("/trigger", response_model=DAGTriggerResponse)
async def trigger_push_dag(strategy_name: str = Form(...)):
    """Airflow経由でGitHubにPushするDAGをトリガー"""
    strategy_name = strategy_name.strip()
    if not strategy_name:
        raise HTTPException(status_code=400, detail="戦略名（strategy_name）が空です。")

    dag_id = "veritas_push_dag"
    dag_run_id = f"manual_push__{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    airflow_url = os.getenv("AIRFLOW_BASE_URL", "http://airflow-webserver:8080")
    dag_trigger_url = f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns"
    
    logging.info(f"DAG『{dag_id}』の起動を試みます。対象戦略: {strategy_name}")

    payload = {"dag_run_id": dag_run_id, "conf": {"strategy_name": strategy_name}}

    try:
        # 実際のAirflow API呼び出し（requestsは非同期でないため、本番ではhttpxの非同期クライアントを推奨）
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                dag_trigger_url,
                auth=(os.getenv("AIRFLOW_USERNAME", "airflow"), os.getenv("AIRFLOW_PASSWORD", "airflow")),
                json=payload,
                timeout=15
            )
            response.raise_for_status() # HTTPエラーがあれば例外を発生させる
        
        logging.info(f"DAGトリガー成功。Run ID: {dag_run_id}")
        return {"detail": f"✅ DAGトリガー成功 (Run ID: {dag_run_id})", "dag_run_id": dag_run_id}

    except httpx.HTTPStatusError as e:
        logging.error(f"Airflow APIエラー (HTTP {e.response.status_code}): {e.response.text}")
        return {"detail": f"❌ Airflowエラー応答 (HTTP {e.response.status_code})", "response_body": e.response.text}
    except Exception as e:
        logging.error(f"Airflowへの通信に失敗しました: {e}", exc_info=True)
        return {"detail": f"🚨 Airflow通信失敗: {e}"}

@router.get("/history", response_class=HTMLResponse)
def view_push_history(
    request: Request,
    sort: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    logs: List[Dict[str, Any]] = Depends(get_filtered_push_logs)
):
    """フィルタリングされたPush履歴を表示する"""
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=(sort != "asc"))
    
    tag_list = sorted({log.get("tag") for log in logs if log.get("tag")})

    total_count = len(logs)
    page_size = 50
    total_pages = max((total_count + page_size - 1) // page_size, 1)
    page = min(page, total_pages)
    start_idx = (page - 1) * page_size
    
    return templates.TemplateResponse("push_history.html", {
        "request": request,
        "logs": logs[start_idx : start_idx + page_size],
        "tag_list": tag_list,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page,
    })

@router.get("/export")
def export_push_history_csv(logs: List[Dict[str, Any]] = Depends(get_filtered_push_logs)):
    """現在のフィルタ条件でPush履歴をCSV形式でエクスポートする"""
    if not logs:
        raise HTTPException(status_code=404, detail="エクスポート対象のログが見つかりません。")

    output = io.StringIO()
    fieldnames = ["timestamp", "strategy", "tag", "message", "signature"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(logs)

    output.seek(0)
    filename = f"push_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

@router.get("/detail/{log_timestamp}", response_class=HTMLResponse)
def push_history_detail(request: Request, log_timestamp: str):
    """特定のPushログの詳細を表示する"""
    log_path = PUSH_LOG_DIR / f"{log_timestamp}.json"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="指定されたログファイルが見つかりません。")

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ログファイルの読み込みに失敗しました: {e}")

    return templates.TemplateResponse("push_history_detail.html", {
        "request": request,
        "log": log
    })
