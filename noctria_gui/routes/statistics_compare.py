from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR

from collections import defaultdict
from statistics import mean, median
from datetime import datetime
from pathlib import Path
import os
import json
import csv
import io
from typing import Optional, List, Dict, Any

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def load_strategy_logs() -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    log_dir = Path(ACT_LOG_DIR)
    for file in os.listdir(log_dir):
        if file.endswith(".json"):
            path = log_dir / file
            try:
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                    if isinstance(obj, dict):
                        data.append(obj)
            except Exception:
                continue
    return data


def filter_by_date(records: List[Dict[str, Any]], from_date: Optional[datetime], to_date: Optional[datetime]) -> List[Dict[str, Any]]:
    filtered = []
    for d in records:
        ts_str = d.get("timestamp", "")[:10]
        ts = parse_date(ts_str)
        if from_date and ts and ts < from_date:
            continue
        if to_date and ts and ts > to_date:
            continue
        filtered.append(d)
    return filtered


def compute_statistics_grouped(data: List[Dict[str, Any]], mode: str) -> Dict[str, Dict[str, List[float]]]:
    stat_map: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for entry in data:
        keys = [entry.get("strategy_name")] if mode == "strategy" else entry.get("tags", [])
        if not keys:
            continue
        for key in keys:
            if not key:
                continue
            for k, v in entry.get("scores", {}).items():
                if isinstance(v, (int, float)):
                    stat_map[key][k].append(v)
    return stat_map


# ==============================
# フォーム表示用ルート追加
# ==============================
@router.get("/statistics/compare/form", response_class=HTMLResponse)
async def compare_form(request: Request):
    all_logs = load_strategy_logs()
    strategies = []
    seen = set()
    for log in all_logs:
        strat_name = log.get("strategy")
        if strat_name and strat_name not in seen:
            seen.add(strat_name)
            strategies.append({
                "strategy": strat_name,
                "win_rate": round(log.get("win_rate", 0)*100, 2),
                "max_drawdown": round(log.get("max_drawdown", 0)*100, 2),
                "num_trades": log.get("num_trades", 0),
            })

    return templates.TemplateResponse("strategies/compare_form.html", {
        "request": request,
        "strategies": strategies,
    })


# ==============================
# 互換リダイレクト: /statistics/compare → /strategies/compare
# ==============================
@router.get("/statistics/compare", include_in_schema=False)
async def legacy_statistics_compare_redirect(request: Request):
    query = request.url.query
    url = "/strategies/compare"
    if query:
        url += f"?{query}"
    return RedirectResponse(url=url, status_code=307)


@router.get("/statistics/compare/export", include_in_schema=False)
async def legacy_statistics_export_redirect(request: Request):
    query = request.url.query
    url = "/strategies/compare/export"
    if query:
        url += f"?{query}"
    return RedirectResponse(url=url, status_code=307)


# ==============================
# メイン: 戦略比較画面
# ==============================
@router.get("/strategies/compare", response_class=HTMLResponse)
async def compare(request: Request) -> HTMLResponse:
    mode = request.query_params.get("mode", "strategy")
    from_date = parse_date(request.query_params.get("from"))
    to_date = parse_date(request.query_params.get("to"))
    sort = request.query_params.get("sort", "score")
    keys = request.query_params.getlist(f"{mode}s")

    all_data = load_strategy_logs()
    filtered = filter_by_date(all_data, from_date, to_date)
    stat_map = compute_statistics_grouped(filtered, mode)

    results = []
    for key, scores in stat_map.items():
        if keys and key not in keys:
            continue
        row = {
            "key": key,
            "avg_win": round(mean(scores["win_rate"]), 2) if scores["win_rate"] else 0,
            "avg_dd": round(mean(scores["max_drawdown"]), 2) if scores["max_drawdown"] else 0,
            "count": len(scores["win_rate"])
        }
        results.append(row)

    if sort == "check":
        results.sort(key=lambda x: keys.index(x["key"]) if x["key"] in keys else 9999)
    else:
        results.sort(key=lambda x: (-x["avg_win"], x["avg_dd"]))

    summary = {
        "avg_win_mean": round(mean([r["avg_win"] for r in results]), 2) if results else 0,
        "avg_win_median": round(median([r["avg_win"] for r in results]), 2) if results else 0,
        "avg_dd_mean": round(mean([r["avg_dd"] for r in results]), 2) if results else 0,
        "avg_dd_median": round(median([r["avg_dd"] for r in results]), 2) if results else 0,
        "total_count": sum(r["count"] for r in results)
    }

    all_keys = sorted(stat_map.keys())

    return templates.TemplateResponse("statistics/statistics_compare.html", {
        "request": request,
        "mode": mode,
        "sort": sort,
        "keys": keys,
        "all_keys": all_keys,
        "results": results,
        "summary": summary,
        "filter": {
            "from": request.query_params.get("from", ""),
            "to": request.query_params.get("to", ""),
        }
    })


@router.get("/strategies/compare/export")
async def export_csv(request: Request) -> StreamingResponse:
    mode = request.query_params.get("mode", "strategy")
    from_date = parse_date(request.query_params.get("from"))
    to_date = parse_date(request.query_params.get("to"))
    keys = request.query_params.getlist(f"{mode}s")

    all_data = load_strategy_logs()
    filtered = filter_by_date(all_data, from_date, to_date)
    stat_map = compute_statistics_grouped(filtered, mode)

    rows = []
    for key, scores in stat_map.items():
        if keys and key not in keys:
            continue
        row = {
            "key": key,
            "avg_win": round(mean(scores["win_rate"]), 2) if scores["win_rate"] else "",
            "avg_dd": round(mean(scores["max_drawdown"]), 2) if scores["max_drawdown"] else "",
            "count": len(scores["win_rate"])
        }
        rows.append(row)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["key", "avg_win", "avg_dd", "count"])
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=compare_result.csv"
    })
