#!/usr/bin/env python3
# coding: utf-8

"""
📊 統計比較ページルート
- 勝率・最大DDの平均を戦略名またはタグ単位で比較
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR

from pathlib import Path
import os
import json
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/statistics", tags=["statistics"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def load_strategy_logs() -> List[Dict[str, Any]]:
    data = []
    act_dir = Path(ACT_LOG_DIR)
    for file in os.listdir(act_dir):
        if file.endswith(".json"):
            try:
                with open(act_dir / file, "r", encoding="utf-8") as f:
                    record = json.load(f)
                data.append(record)
            except Exception:
                continue
    return data


def compute_comparison(
    data: List[Dict[str, Any]],
    mode: str,
    keys: List[str],
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    sort_mode: str = "score"
) -> List[Dict[str, Any]]:
    result = defaultdict(lambda: {"count": 0, "win_sum": 0.0, "dd_sum": 0.0})

    for record in data:
        try:
            date_str = record.get("date")
            if not date_str:
                continue
            date = parse_date(date_str)
            if not date:
                continue
            if from_date and date < from_date:
                continue
            if to_date and date > to_date:
                continue

            score = record.get("score", {})
            win = score.get("win_rate")
            dd = score.get("max_drawdown")

            record_keys = record.get("tags", []) if mode == "tag" else [record.get("strategy_name")]

            for key in record_keys:
                if not key or key not in keys:
                    continue
                result[key]["count"] += 1
                if isinstance(win, (int, float)):
                    result[key]["win_sum"] += win
                if isinstance(dd, (int, float)):
                    result[key]["dd_sum"] += dd
        except Exception:
            continue

    final = []
    for k in keys:
        if k not in result:
            continue
        v = result[k]
        count = v["count"]
        avg_win = round(v["win_sum"] / count, 1) if count else 0
        avg_dd = round(v["dd_sum"] / count, 1) if count else 0
        final.append({
            "key": k,
            "avg_win": avg_win,
            "avg_dd": avg_dd,
            "count": count
        })

    if sort_mode == "score":
        final.sort(key=lambda x: (-x["avg_win"], x["avg_dd"]))
    elif sort_mode == "check":
        final = sorted(final, key=lambda x: keys.index(x["key"]))  # preserve user selection order

    return final


def extract_all_keys(data: List[Dict[str, Any]], mode: str) -> List[str]:
    key_set = set()
    for record in data:
        if mode == "tag":
            key_set.update(record.get("tags", []))
        else:
            name = record.get("strategy_name")
            if name:
                key_set.add(name)
    return sorted(key_set)


@router.get("/compare", response_class=HTMLResponse)
async def compare_statistics(request: Request) -> HTMLResponse:
    params = request.query_params
    mode = params.get("mode", "tag")  # "strategy" or "tag"
    sort = params.get("sort", "score")
    keys = params.get(mode + "s", "").split(",")
    keys = [k.strip() for k in keys if k.strip()]
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))

    all_data = load_strategy_logs()
    result = compute_comparison(all_data, mode, keys, from_date, to_date, sort)
    all_keys = extract_all_keys(all_data, mode)

    return templates.TemplateResponse("statistics/statistics_compare.html", {
        "request": request,
        "mode": mode,
        "keys": keys,
        "all_keys": all_keys,
        "results": result,
        "sort": sort,
        "filter": {
            "mode": mode,
            "from": params.get("from", ""),
            "to": params.get("to", ""),
        }
    })


# --- 古いルート対策のリダイレクト ---
@router.get("/../strategy/compare")
async def redirect_old_strategy_compare():
    return RedirectResponse(url="/statistics/compare")
