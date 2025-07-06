# routes/statistics_ranking.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR

from collections import defaultdict
from datetime import datetime
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


def load_tag_statistics(from_date=None, to_date=None, tag_keyword=None):
    tag_stats = defaultdict(lambda: {"count": 0, "win_rates": [], "drawdowns": []})

    for file in os.listdir(ACT_LOG_DIR):
        if not file.endswith(".json"):
            continue
        try:
            with open(ACT_LOG_DIR / file, "r", encoding="utf-8") as f:
                data = json.load(f)

            date_str = data.get("date")
            if not date_str:
                continue
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

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
                tag_stats[tag]["count"] += 1
                if isinstance(win, (int, float)):
                    tag_stats[tag]["win_rates"].append(win)
                if isinstance(dd, (int, float)):
                    tag_stats[tag]["drawdowns"].append(dd)
        except Exception:
            continue

    final_stats = []
    for tag, stats in tag_stats.items():
        win_avg = round(sum(stats["win_rates"]) / len(stats["win_rates"]), 1) if stats["win_rates"] else None
        dd_avg = round(sum(stats["drawdowns"]) / len(stats["drawdowns"]), 1) if stats["drawdowns"] else None
        final_stats.append({
            "tag": tag,
            "count": stats["count"],
            "avg_win": win_avg,
            "avg_dd": dd_avg,
        })

    return final_stats


@router.get("/statistics/ranking", response_class=HTMLResponse)
async def tag_ranking(request: Request):
    """
    🏅 タグ別ランキング表示（勝率・安定性・件数）
    """
    params = request.query_params
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))
    tag_keyword = params.get("tag")

    stats = load_tag_statistics(from_date, to_date, tag_keyword)

    ranking_win = sorted([s for s in stats if s["avg_win"] is not None], key=lambda x: x["avg_win"], reverse=True)
    ranking_dd = sorted([s for s in stats if s["avg_dd"] is not None], key=lambda x: x["avg_dd"])
    ranking_count = sorted(stats, key=lambda x: x["count"], reverse=True)

    return templates.TemplateResponse("statistics_ranking.html", {
        "request": request,
        "ranking_win": ranking_win[:10],
        "ranking_dd": ranking_dd[:10],
        "ranking_count": ranking_count[:10],
        "filter": {
            "from": params.get("from") or "",
            "to": params.get("to") or "",
            "tag": tag_keyword or ""
        }
    })


@router.get("/statistics/ranking/export")
async def export_tag_ranking_csv(request: Request):
    """
    📁 タグ別ランキング（CSVエクスポート）
    """
    params = request.query_params
    from_date = parse_date(params.get("from"))
    to_date = parse_date(params.get("to"))
    tag_keyword = params.get("tag")

    stats = load_tag_statistics(from_date, to_date, tag_keyword)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["タグ", "件数", "平均勝率（%）", "最大DD（%）"])

    for s in stats:
        writer.writerow([s["tag"], s["count"], s["avg_win"], s["avg_dd"]])

    buffer.seek(0)
    filename = "tag_ranking.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
