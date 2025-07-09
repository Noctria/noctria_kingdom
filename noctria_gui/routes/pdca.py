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
    recheck_status: str = Query(default=None),
    diff_filter: str = Query(default=None),  # ✅ 差分フィルター
    recheck_success: int = Query(default=None),
    recheck_fail: int = Query(default=None),
):
    logs = []
    tag_set = set()

    # ステータス抽出マップ（success/fail）
    status_map = {}
    latest_status = {}

    for log_file in sorted(PDCA_LOG_DIR.glob("*.json"), reverse=True):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        strategy_name = data.get("strategy")
        status = data.get("status")
        ts = data.get("timestamp")

        if strategy_name and status:
            prev_ts = latest_status.get(strategy_name, {}).get("timestamp", "")
            if not prev_ts or ts > prev_ts:
                latest_status[strategy_name] = {
                    "status": status,
                    "timestamp": ts,
                }

    for strategy_name, info in latest_status.items():
        status_map[strategy_name] = info["status"]

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
            "trades": data.get("trades"),
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
        if recheck_status:
            try:
                parsed = json.loads(log["json_text"])
                has_recheck = "recheck_timestamp" in parsed
                if recheck_status == "done" and not has_recheck:
                    return False
                if recheck_status == "pending" and has_recheck:
                    return False
            except Exception:
                return False
        if diff_filter:
            try:
                parsed = json.loads(log["json_text"])
                wr_b = parsed.get("win_rate_before")
                wr_a = parsed.get("win_rate_after")
                dd_b = parsed.get("max_dd_before")
                dd_a = parsed.get("max_dd_after")
                if diff_filter == "win_rate_up" and (wr_b is None or wr_a is None or wr_a <= wr_b):
                    return False
                if diff_filter == "max_dd_down" and (dd_b is None or dd_a is None or dd_a >= dd_b):
                    return False
            except Exception:
                return False
        return True

    filtered_logs = [log for log in logs if matches(log)]

    if sort:
        reverse = sort.startswith("-")
        key = sort.lstrip("-")
        if key in ["win_rate", "max_dd", "trades", "timestamp_dt", "win_rate_diff", "max_dd_diff"]:
            filtered_logs.sort(key=lambda x: x.get(key) or 0, reverse=reverse)

    def make_json_serializable(log):
        new_log = log.copy()
        for key in ["timestamp_dt"]:
            val = new_log.get(key)
            if isinstance(val, datetime):
                new_log[key] = val.isoformat()

        try:
            parsed = json.loads(new_log["json_text"])
            wr_b = parsed.get("win_rate_before")
            wr_a = parsed.get("win_rate_after")
            new_log["win_rate_diff"] = wr_a - wr_b if wr_a is not None and wr_b is not None else None
            dd_b = parsed.get("max_dd_before")
            dd_a = parsed.get("max_dd_after")
            new_log["max_dd_diff"] = dd_a - dd_b if dd_a is not None and dd_b is not None else None
        except Exception:
            new_log["win_rate_diff"] = None
            new_log["max_dd_diff"] = None

        return new_log

    logs_serializable = [make_json_serializable(log) for log in filtered_logs]

    return templates.TemplateResponse("pdca_history.html", {
        "request": request,
        "logs": logs_serializable,
        "status_map": status_map,
        "filters": {
            "strategy": strategy or "",
            "symbol": symbol or "",
            "signal": signal or "",
            "tag": tag or "",
            "date_from": date_from or "",
            "date_to": date_to or "",
        },
        "recheck_status": recheck_status or "",
        "diff_filter": diff_filter or "",
        "sort": sort or "",
        "available_tags": sorted(tag_set),
        "recheck_success": recheck_success,
        "recheck_fail": recheck_fail,
    })
