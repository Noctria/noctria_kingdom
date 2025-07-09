from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import os
import json
import requests
from urllib.parse import urlencode

from core.path_config import (
    PDCA_LOG_DIR,
    NOCTRIA_GUI_TEMPLATES_DIR,
    STRATEGIES_VERITAS_GENERATED_DIR,
)

from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080/api/v1")
AIRFLOW_API_USER = os.getenv("AIRFLOW_API_USER", "admin")
AIRFLOW_API_PASSWORD = os.getenv("AIRFLOW_API_PASSWORD", "admin")


@router.get("/pdca", response_class=HTMLResponse)
async def show_pdca_dashboard(
    request: Request,
    strategy: str = Query(default=None),
    symbol: str = Query(default=None),
    signal: str = Query(default=None),
    tag: str = Query(default=None),
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
    sort: str = Query(default=None),
    diff_filter: str = Query(default=None),
    win_rate_min_diff: float = Query(default=None),
    recheck_success: int = Query(default=None),
    recheck_fail: int = Query(default=None),
):
    logs = []
    tag_set = set()

    for log_file in sorted(PDCA_LOG_DIR.glob("*.json"), reverse=True):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ ログ読み込み失敗: {log_file} -> {e}")
            continue

        ts = data.get("timestamp", "")
        try:
            ts_dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            ts_dt = None

        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        tag_set.update(tags)

        logs.append({
            "filename": log_file.name,
            "path": str(log_file),
            "strategy": data.get("strategy", "N/A"),
            "timestamp": ts,
            "timestamp_dt": ts_dt,
            "signal": data.get("signal", "N/A"),
            "symbol": data.get("symbol", "N/A"),
            "lot": data.get("lot", "N/A"),
            "tp": data.get("tp", "N/A"),
            "sl": data.get("sl", "N/A"),
            "win_rate": data.get("win_rate"),
            "max_dd": data.get("max_dd"),
            "win_rate_before": data.get("win_rate_before"),
            "win_rate_after": data.get("win_rate_after"),
            "max_dd_before": data.get("max_dd_before"),
            "max_dd_after": data.get("max_dd_after"),
            "tags": tags,
            "json_text": json.dumps(data, indent=2, ensure_ascii=False),
        })

    def matches(log):
        if strategy and strategy.lower() not in log["strategy"].lower():
            return False
        if symbol and symbol != log["symbol"]:
            return False
        if signal and signal != log["signal"]:
            return False
        if tag and tag not in log["tags"]:
            return False
        if date_from:
            try:
                from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                if log["timestamp_dt"] and log["timestamp_dt"] < from_dt:
                    return False
            except Exception:
                pass
        if date_to:
            try:
                to_dt = datetime.strptime(date_to, "%Y-%m-%d")
                if log["timestamp_dt"] and log["timestamp_dt"] > to_dt:
                    return False
            except Exception:
                pass

        # 差分フィルター
        try:
            if diff_filter == "win_rate_up":
                if log["win_rate_after"] is None or log["win_rate_before"] is None:
                    return False
                if log["win_rate_after"] <= log["win_rate_before"]:
                    return False
            elif diff_filter == "max_dd_down":
                if log["max_dd_after"] is None or log["max_dd_before"] is None:
                    return False
                if log["max_dd_after"] >= log["max_dd_before"]:
                    return False
        except Exception:
            return False

        # しきい値フィルター
        if win_rate_min_diff is not None:
            try:
                wr_b = log.get("win_rate_before")
                wr_a = log.get("win_rate_after")
                if wr_b is None or wr_a is None or (wr_a - wr_b) < win_rate_min_diff:
                    return False
            except Exception:
                return False

        return True

    filtered_logs = [log for log in logs if matches(log)]

    if sort:
        reverse = sort.startswith("-")
        key = sort.lstrip("-")
        if key in ["win_rate", "max_dd", "trades", "timestamp_dt"]:
            filtered_logs.sort(key=lambda x: x.get(key) or 0, reverse=reverse)

    return templates.TemplateResponse("pdca_history.html", {
        "request": request,
        "logs": filtered_logs,
        "filters": {
            "strategy": strategy or "",
            "symbol": symbol or "",
            "signal": signal or "",
            "tag": tag or "",
            "date_from": date_from or "",
            "date_to": date_to or "",
        },
        "sort": sort or "",
        "available_tags": sorted(tag_set),
        "diff_filter": diff_filter or "",
        "win_rate_min_diff": win_rate_min_diff or "",
        "recheck_success": recheck_success,
        "recheck_fail": recheck_fail,
    })
