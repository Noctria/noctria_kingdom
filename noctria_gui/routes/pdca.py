from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import os
import json
from dotenv import load_dotenv

from src.core.path_config import (
    PDCA_LOG_DIR,
    NOCTRIA_GUI_TEMPLATES_DIR,
)

load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

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

        ts_str = data.get("timestamp", "")
        try:
            ts_dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
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
            "timestamp": ts_str,
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
        try:
            if strategy and strategy.lower() not in log["strategy"].lower():
                return False
            if symbol and symbol != log["symbol"]:
                return False
            if signal and signal != log["signal"]:
                return False
            if tag and tag not in log["tags"]:
                return False
            if date_from:
                from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                if log["timestamp_dt"] and log["timestamp_dt"] < from_dt:
                    return False
            if date_to:
                to_dt = datetime.strptime(date_to, "%Y-%m-%d")
                if log["timestamp_dt"] and log["timestamp_dt"] > to_dt:
                    return False

            if diff_filter == "win_rate_up":
                before = log.get("win_rate_before")
                after = log.get("win_rate_after")
                if before is None or after is None or after <= before:
                    return False

            if diff_filter == "max_dd_down":
                before = log.get("max_dd_before")
                after = log.get("max_dd_after")
                if before is None or after is None or after >= before:
                    return False

            if win_rate_min_diff is not None:
                before = log.get("win_rate_before")
                after = log.get("win_rate_after")
                if before is None or after is None or (after - before) < win_rate_min_diff:
                    return False

        except Exception:
            return False

        return True

    filtered_logs = [log for log in logs if matches(log)]

    # ソート処理
    if sort:
        reverse = sort.startswith("-")
        sort_key = sort.lstrip("-")
        if sort_key in ["timestamp_dt", "win_rate", "max_dd"]:
            filtered_logs.sort(
                key=lambda x: x.get(sort_key) if x.get(sort_key) is not None else 0,
                reverse=reverse
            )

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
