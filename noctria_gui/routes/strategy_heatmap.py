from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR

from collections import defaultdict
from datetime import datetime
from pathlib import Path
import os
import json
import io
import csv

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None

def load_strategy_stats(from_date=None, to_date=None, strategy_keyword=None):
    stats = defaultdict(lambda: {"count": 0, "win_rates": [], "drawdowns": []})
    act_dir = Path(ACT_LOG_DIR)

    for file in os.listdir(act_dir):
        if not file.endswith(".json"):
            continue
        try:
            with open(act_dir / file, "r", encoding="utf-8") as f:
                data = json.load(f)

            date_str = data.get("date")
            if not date_str:
                continue
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            if from_date and date_obj < from_date:
                continue
            if to_date and date_obj > to_date:
                continue

            name = data.get("strategy_name", "").strip()
            if not name:
                continue
            if strategy_keyword and strategy_keyword.lower() not in name.lower():
                continue

            score = data.get("score", {})
            win = score.get("win_rate")
            dd = score.get("max_drawdown")

            stats[name]["count"] += 1
            if isinstance(win, (int, float)):
                stats[name]["win_rates"].append(win)
            if isinstance(dd, (int, float)):
                stats[name]["drawdowns"].append(dd)
        except Exception:
            continue

    final_stats = {}
    for name, values in stats.items():
        count = values["count"]
        win_avg = round(sum(values["win_rates"]) / len(values["win_rates"]), 1) if values["win_rates"] else None
        dd_avg = round(sum(values["drawdowns"]) / len(values["drawdowns"]), 1) if values["drawdowns"] else None
        final_stats[name] = {
            "count": count,
            "avg_win": win_avg,
            "avg_dd": dd_avg,
        }
    return final_stats

@router.get("/statistics/strategy-heatmap", response_class=HTMLResponse)
async def strategy_heatmap(request: Request):
    """
    🧠 戦略別統計ヒートマップ（GUI表示）
    """
    params = request.query_params
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))
    strategy_keyword = params.get("strategy")

    stats = load_strategy_stats(from_date, to_date, strategy_keyword)

    return templates.TemplateResponse("strategy_heatmap.html", {
        "request": request,
        "data": stats,
        "filter": {
            "from": params.get("from") or "",
            "to": params.get("to") or "",
            "strategy": strategy_keyword or ""
        }
    })

@router.get("/statistics/strategy-heatmap/export")
async def export_strategy_heatmap_csv(request: Request):
    """
    📁 戦略別統計ヒートマップのCSV出力
    """
    params = request.query_params
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))
    strategy_keyword = params.get("strategy")

    stats = load_strategy_stats(from_date, to_date, strategy_keyword)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["戦略名", "件数", "平均勝率（%）", "最大DD（%）"])
    for name, v in stats.items():
        writer.writerow([name, v["count"], v["avg_win"], v["avg_dd"]])

    buffer.seek(0)
    filename = "strategy_heatmap.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
