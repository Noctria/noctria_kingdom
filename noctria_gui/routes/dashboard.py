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
from typing import Optional, Dict, Any

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """'YYYY-MM-DD'形式の日付文字列→datetime。エラー時None"""
    try:
        if not date_str:
            return None
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None

def load_tag_stats(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    tag_keyword: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    タグごとに勝率・DDなどを集計。
    """
    tag_stats = defaultdict(lambda: {"count": 0, "win_rates": [], "drawdowns": []})
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

            # 期間フィルタ
            if from_date and date_obj < from_date:
                continue
            if to_date and date_obj > to_date:
                continue

            tags = data.get("tags", [])
            if tag_keyword and not any(tag_keyword.lower() in t.lower() for t in tags):
                continue

            score = data.get("score", {})
            win = score.get("win_rate")
            dd = score.get("max_drawdown")

            for tag in tags:
                t = tag.strip()
                tag_stats[t]["count"] += 1
                if isinstance(win, (int, float)):
                    tag_stats[t]["win_rates"].append(win)
                if isinstance(dd, (int, float)):
                    tag_stats[t]["drawdowns"].append(dd)
        except Exception:
            continue

    # 平均値など整形
    final_stats = {}
    for tag, values in tag_stats.items():
        count = values["count"]
        win_avg = round(sum(values["win_rates"]) / len(values["win_rates"]), 1) if values["win_rates"] else None
        dd_avg = round(sum(values["drawdowns"]) / len(values["drawdowns"]), 1) if values["drawdowns"] else None
        final_stats[tag] = {
            "count": count,
            "avg_win": win_avg,
            "avg_dd": dd_avg,
        }
    return final_stats

@router.get("/statistics/heatmap", response_class=HTMLResponse)
async def heatmap(request: Request):
    """
    📊 タグ別統計ヒートマップ（GUI表示）
    """
    params = request.query_params
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))
    tag_keyword = params.get("tag")

    stats = load_tag_stats(from_date, to_date, tag_keyword)

    return templates.TemplateResponse("scoreboard.html", {
        "request": request,
        "data": stats,
        "filter": {
            "from": params.get("from") or "",
            "to": params.get("to") or "",
            "tag": tag_keyword or ""
        }
    })

@router.get("/statistics/heatmap/export")
async def export_heatmap_csv(request: Request):
    """
    📁 タグ別統計ヒートマップのCSV出力
    """
    params = request.query_params
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))
    tag_keyword = params.get("tag")

    stats = load_tag_stats(from_date, to_date, tag_keyword)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["タグ", "件数", "平均勝率（%）", "最大DD（%）"])
    for tag, v in stats.items():
        writer.writerow([tag, v["count"], v["avg_win"], v["avg_dd"]])

    buffer.seek(0)
    filename = "tag_heatmap.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
