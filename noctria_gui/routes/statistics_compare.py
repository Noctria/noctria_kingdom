# routes/statistics_compare.py（抜粋、エクスポート部含む全体）

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR
from collections import defaultdict
from statistics import mean, median
import os, json, csv, io
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None

def load_strategy_logs():
    data = []
    for file in os.listdir(ACT_LOG_DIR):
        if file.endswith(".json"):
            with open(os.path.join(ACT_LOG_DIR, file), "r") as f:
                try:
                    data.append(json.load(f))
                except:
                    continue
    return data

@router.get("/statistics/compare", response_class=HTMLResponse)
async def compare(request: Request):
    mode = request.query_params.get("mode", "strategy")
    from_date = parse_date(request.query_params.get("from"))
    to_date = parse_date(request.query_params.get("to"))
    all_data = load_strategy_logs()

    filtered = []
    for d in all_data:
        ts = parse_date(d.get("timestamp", "")[:10])
        if from_date and ts and ts < from_date:
            continue
        if to_date and ts and ts > to_date:
            continue
        filtered.append(d)

    # 集約
    stat_map = defaultdict(lambda: defaultdict(list))
    for entry in filtered:
        keys = [entry["strategy_name"]] if mode == "strategy" else entry.get("tags", [])
        for key in keys:
            for k, v in entry.get("scores", {}).items():
                stat_map[key][k].append(v)

    # 整形
    results = []
    for key, scores in stat_map.items():
        flat = { "name": key }
        for metric, values in scores.items():
            flat[f"{metric}_mean"] = round(mean(values), 3)
            flat[f"{metric}_median"] = round(median(values), 3)
        results.append(flat)

    return templates.TemplateResponse("statistics_compare.html", {
        "request": request,
        "mode": mode,
        "data": results,
        "filter": { "from": request.query_params.get("from", ""), "to": request.query_params.get("to", "") },
    })

@router.get("/statistics/compare/export")
async def export_csv(request: Request):
    mode = request.query_params.get("mode", "strategy")
    from_date = parse_date(request.query_params.get("from"))
    to_date = parse_date(request.query_params.get("to"))
    all_data = load_strategy_logs()

    filtered = []
    for d in all_data:
        ts = parse_date(d.get("timestamp", "")[:10])
        if from_date and ts and ts < from_date:
            continue
        if to_date and ts and ts > to_date:
            continue
        filtered.append(d)

    stat_map = defaultdict(lambda: defaultdict(list))
    for entry in filtered:
        keys = [entry["strategy_name"]] if mode == "strategy" else entry.get("tags", [])
        for key in keys:
            for k, v in entry.get("scores", {}).items():
                stat_map[key][k].append(v)

    rows = []
    headers = ["name"]
    metric_names = set()
    for key, scores in stat_map.items():
        row = {"name": key}
        for metric, values in scores.items():
            m = round(mean(values), 3)
            med = round(median(values), 3)
            row[f"{metric}_mean"] = m
            row[f"{metric}_median"] = med
            metric_names.update([f"{metric}_mean", f"{metric}_median"])
        rows.append(row)

    headers.extend(sorted(metric_names))

    # 統計行追加
    summary_mean = {"name": "📊 平均"}
    summary_median = {"name": "📊 中央値"}
    for metric in metric_names:
        values = [row[metric] for row in rows if metric in row]
        if values:
            summary_mean[metric] = round(mean(values), 3)
            summary_median[metric] = round(median(values), 3)
        else:
            summary_mean[metric] = ""
            summary_median[metric] = ""

    rows.extend([summary_mean, summary_median])

    # CSV 出力
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename=compare_result.csv"
    })
