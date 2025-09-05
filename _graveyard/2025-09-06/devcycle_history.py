# noctria_gui/routes/devcycle_history.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import psycopg2
import json
from datetime import datetime
from decimal import Decimal
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR  # 共通パス管理

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def _decimal_to_float(obj):
    """再帰的にDecimal型をfloat化（dict/リスト/単体対応）"""
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_decimal_to_float(v) for v in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj

def fetch_devcycle_history(limit=100):
    db = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "user": os.getenv("DB_USER", "airflow"),
        "password": os.getenv("DB_PASSWORD", "airflow"),
        "dbname": os.getenv("DB_NAME", "airflow"),
    }
    conn = psycopg2.connect(**db)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, turn_number, started_at, finished_at, passed_tests, total_tests, pass_rate,
               generated_files, review_comments, failed, fail_reason, extra_info, created_at
        FROM ai_devcycle_turn_history
        ORDER BY id DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    keys = [
        "id", "turn_number", "started_at", "finished_at", "passed_tests", "total_tests", "pass_rate",
        "generated_files", "review_comments", "failed", "fail_reason", "extra_info", "created_at"
    ]
    history = []
    for row in rows:
        record = dict(zip(keys, row))
        # extra_infoはJSONデコード
        if isinstance(record["extra_info"], str):
            try:
                record["extra_info"] = json.loads(record["extra_info"])
            except Exception:
                record["extra_info"] = {}
        # Decimal型をfloat化
        record = _decimal_to_float(record)
        history.append(record)
    return list(reversed(history))  # 昇順（古い→新しい順）にする

@router.get("/devcycle/history", response_class=HTMLResponse)
async def devcycle_history(request: Request):
    history = fetch_devcycle_history(50)
    return templates.TemplateResponse("devcycle_history.html", {
        "request": request,
        "history": history,
    })
